import search
import bank

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
        self.bank = bank.english_word_bank()
        capabilities = DesiredCapabilities.CHROME
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}
        self.driver = webdriver.Chrome(
            r"drivers/chromedriver",
            desired_capabilities=capabilities,
        )

    def connect(self):
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
        # Main loop: try joining a game, then playing, then repeating
        # Additionally, make sure that we are monitoring the websocket for messages
        srch = search.WordSearch(self.bank)
        joined = False
        self_pid = -2
        turn_pid = -1
        turn_prefix = ""
        last_word = ""
        self_last_mask = 0
        self_mask = 0
        while True:
            logs = self.driver.get_log("performance")
            for entry in logs:
                log = json.loads(entry["message"])["message"]
                method = log["method"]
                if method == "Network.webSocketFrameReceived":
                    payload = log["params"]["response"]["payloadData"]
                    if payload.startswith("42["):
                        payload = json.loads(payload[2:])
                        print(payload)
                        if payload[0] == "setup":
                            settings = payload[1]
                            self_pid = settings['selfPeerId']
                        elif payload[0] == "setMilestone":
                            settings = payload[1]
                            if settings['name'] == 'round':
                                turn_pid = settings['currentPlayerPeerId']
                                turn_prefix = settings['syllable']
                            elif settings['name'] == 'seating':
                                srch = search.WordSearch(self.bank)
                                joined = False
                                turn_pid = -1
                                turn_prefix = ""
                                last_word = ""
                        elif payload[0] == "nextTurn":
                            turn_pid = payload[1]
                            turn_prefix = payload[2]
                        elif payload[0] == "setPlayerWord":
                            last_word = payload[2]
                        elif payload[0] == "correctWord":
                            srch.use(last_word)
                            if payload[1]["playerPeerId"] == self_pid:
                                self_mask |= self_last_mask
                        elif payload[0] == "failWord":
                            srch.use(last_word)
                        elif payload[0] == "bonusAlphabetCompleted":
                            if payload[1] == self_pid:
                                self_mask = 0
            if joined:
                if self_pid == turn_pid:
                    actions = ActionChains(self.driver)
                    (word, mask) = srch.search(turn_prefix, self_mask)
                    actions.send_keys(word + Keys.RETURN)
                    actions.perform()
                    self_last_mask = mask
            else:
                time.sleep(1)
                try:
                    button = self.driver.find_element_by_xpath('//button[text()="Join game"]')
                    button.click()
                    joined = True
                except ElementNotInteractableException:
                    pass
