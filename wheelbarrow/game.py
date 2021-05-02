import strategy

import json
import time

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class Game:
    def __init__(self, room: str):
        self.url = 'https://jklm.fun/{}'.format(room)
        self.corpus = strategy.english_corpus()
        capabilities = DesiredCapabilities.CHROME
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}
        self.driver = webdriver.Chrome(
            r"drivers/chromedriver",
            desired_capabilities=capabilities,
        )
        self.pid = -1

    def get_latest_updates(self):
        logs = self.driver.get_log("performance")
        for entry in logs:
            log = json.loads(entry["message"])["message"]
            method = log["method"]
            if method == "Network.webSocketFrameReceived":
                payload = log["params"]["response"]["payloadData"]
                if payload.startswith("42["):
                    payload = json.loads(payload[2:])
                    yield payload

    def start(self):
        # Navigate to the game page
        self.driver.get(self.url)
        # Wait a bit until the page loads and then join the game
        time.sleep(1)
        button = self.driver.find_element_by_xpath('//button[text()="OK"]')
        button.click()
        # Switch into the iframe encapsulating the game
        switched = False
        frame = None
        while not switched:
            frames = self.driver.find_elements_by_xpath('//iframe')
            if len(frames) == 0:
                continue
            frame = frames[0]
            self.driver.switch_to.frame(frame)
            switched = True
        # Wait until we've completed setup before proceeding
        while self.pid == -1:
            for update in self.get_latest_updates():
                action = update[0]
                if action == "setup":
                    print(update)
                    settings = update[1]
                    self.pid = settings['selfPeerId']
                    break
        # Main loop: try joining a round, then playing, then repeating
        while True:
            time.sleep(1)
            try:
                button = self.driver.find_element_by_xpath('//button[text()="Join game"]')
                button.click()
                Round(self).start()
            except ElementNotInteractableException:
                pass


class Round:
    def __init__(self, game: Game):
        self.game = game
        self.started = False
        self.my_pid = self.game.pid
        self.bomb_pid = -2
        self.bomb_syllable = ""
        self.bomb_word = ""
        self.searcher = strategy.Searcher(self.game.corpus)

    def start(self):
        while True:
            # Run through all observed updates to the game state
            for update in self.game.get_latest_updates():
                action = update[0]
                if not self.started:
                    if action == "setMilestone":
                        settings = update[1]
                        if settings['name'] == 'round':
                            print(update)
                            self.bomb_pid = settings['currentPlayerPeerId']
                            self.bomb_syllable = settings['syllable']
                            self.started = True
                else:
                    if action == "setMilestone":
                        settings = update[1]
                        if settings['name'] == 'seating':
                            print(update)
                            return
                    elif action == "nextTurn":
                        print(update)
                        self.bomb_pid = update[1]
                        self.bomb_syllable = update[2]
                    elif action == "setPlayerWord":
                        print(update)
                        self.bomb_word = update[2]
                    elif action == "correctWord":
                        if update[1]["playerPeerId"] == self.my_pid:
                            print(update)
                            self.searcher.confirm_correct(self.bomb_word)
                        else:
                            print(update)
                            self.searcher.confirm_used(self.bomb_word)
                    elif action == "failWord":
                        if update[2] == "notInDictionary":
                            print(update)
                            self.searcher.confirm_used(self.bomb_word)
                    elif action == "bonusAlphabetCompleted":
                        if update[1] == self.my_pid:
                            print(update)
                            self.searcher.confirm_bonus()
            # We are given the bomb, so we should submit a word
            if self.my_pid == self.bomb_pid:
                word = self.searcher.search(self.bomb_syllable)
                if word is not None:
                    actions = ActionChains(self.game.driver)
                    actions.send_keys(word + Keys.RETURN)
                    actions.perform()
