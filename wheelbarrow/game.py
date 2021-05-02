from loguru import logger

import strategy
import json
import time

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class Game:
    def __init__(self, room: str, human: bool):
        self.url = "https://jklm.fun/{}".format(room)
        self.human = human
        capabilities = DesiredCapabilities.CHROME
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}
        self.driver = webdriver.Chrome(
            r"drivers/chromedriver",
            desired_capabilities=capabilities,
        )
        self.pid = -1
        self.corpus = strategy.english_corpus()

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
            try:
                frames = self.driver.find_elements_by_xpath("//iframe")
                if len(frames) == 0:
                    continue
                frame = frames[0]
                self.driver.switch_to.frame(frame)
                switched = True
            except NoSuchElementException:
                pass
        # Wait until we've completed setup before proceeding
        while self.pid == -1:
            for update in self.get_latest_updates():
                action = update[0]
                logger.info("Received game update: {}", update)
                if action == "setup":
                    settings = update[1]
                    self.pid = settings["selfPeerId"]
                    logger.info("Processed game update: {}", update)
                    break
        # Main loop: try joining a round, then playing, then repeating
        while True:
            time.sleep(1)
            try:
                button = self.driver.find_element_by_xpath(
                    '//button[text()="Join game"]'
                )
                button.click()
                Round(self).start()
            except ElementNotInteractableException:
                pass
            except NoSuchElementException:
                pass


class Round:
    def __init__(self, game: Game):
        self.game = game
        self.started = False
        self.my_pid = self.game.pid
        self.my_ready = True
        self.bomb_pid = -2
        self.bomb_syllable = ""
        self.bomb_word = ""
        self.bot = strategy.Bot(game.corpus, game.human)

    def start(self):
        while True:
            # Run through all observed updates to the game state
            for update in self.game.get_latest_updates():
                action = update[0]
                logger.info("Received game update: {}", update)
                if not self.started:
                    if action == "setMilestone":
                        settings = update[1]
                        if settings["name"] == "round":
                            self.bomb_pid = settings["currentPlayerPeerId"]
                            self.bomb_syllable = settings["syllable"]
                            self.started = True
                            logger.info("Processed game update: {}", update)
                else:
                    if action == "setMilestone":
                        settings = update[1]
                        if settings["name"] == "seating":
                            logger.info("Processed game update: {}", update)
                            return
                    elif action == "nextTurn":
                        self.bomb_pid = update[1]
                        self.bomb_syllable = update[2]
                        self.my_ready = True
                        logger.info("Processed game update: {}", update)
                    elif action == "setPlayerWord":
                        self.bomb_word = update[2]
                        logger.info("Processed game update: {}", update)
                    elif action == "correctWord":
                        if update[1]["playerPeerId"] == self.my_pid:
                            self.bot.on_correct_word(self.bomb_word)
                        else:
                            self.bot.on_use_word(self.bomb_word)
                        logger.info("Processed game update: {}", update)
                    elif action == "failWord":
                        if update[1] == self.my_pid:
                            self.bot.on_use_word(self.bomb_word)
                            self.my_ready = True
                        else:
                            self.bot.on_use_word(self.bomb_word)
                        logger.info("Processed game update: {}", update)
                    elif action == "bonusAlphabetCompleted":
                        if update[1] == self.my_pid:
                            self.bot.on_bonus_life()
                        logger.info("Processed game update: {}", update)
            # We are given the bomb, so we should submit a word
            if self.my_pid == self.bomb_pid and self.my_ready:
                actions = self.bot.on_search_syllable(self.bomb_syllable)
                if actions == []:
                    logger.warning("Unable to find word for '{}'!", self.bomb_syllable)
                else:
                    for (action, val) in actions:
                        if action == "wait":
                            time.sleep(val)
                        elif action == "press":
                            actions = ActionChains(self.game.driver)
                            actions.send_keys(val)
                            actions.perform()
                    self.my_ready = False
