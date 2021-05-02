from loguru import logger

import strategy
import json
import time
import random

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
                if action == "setup":
                    print(update)
                    settings = update[1]
                    self.pid = settings["selfPeerId"]
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
        self.searcher = strategy.Searcher(self.game.corpus)
        self.human = self.game.human

    def start(self):
        while True:
            # Run through all observed updates to the game state
            for update in self.game.get_latest_updates():
                action = update[0]
                logger.info("Some update: {}", update)
                if not self.started:
                    if action == "setMilestone":
                        settings = update[1]
                        if settings["name"] == "round":
                            logger.info("Processed game update: {}", update)
                            self.bomb_pid = settings["currentPlayerPeerId"]
                            self.bomb_syllable = settings["syllable"]
                            self.started = True
                else:
                    if action == "setMilestone":
                        settings = update[1]
                        if settings["name"] == "seating":
                            logger.info("Processed game update: {}", update)
                            return
                    elif action == "nextTurn":
                        logger.info("Processed game update: {}", update)
                        self.bomb_pid = update[1]
                        self.bomb_syllable = update[2]
                        self.my_ready = True
                    elif action == "setPlayerWord":
                        logger.info("Processed game update: {}", update)
                        self.bomb_word = update[2]
                    elif action == "correctWord":
                        logger.info("Processed game update: {}", update)
                        if update[1]["playerPeerId"] == self.my_pid:
                            self.searcher.confirm_correct(self.bomb_word)
                        else:
                            self.searcher.confirm_used(self.bomb_word)
                    elif action == "failWord":
                        logger.info("Processed game update: {}", update)
                        if update[1] == self.my_pid:
                            self.searcher.confirm_used(self.bomb_word)
                            self.my_ready = True
                        else:
                            self.searcher.confirm_used(self.bomb_word)
                    elif action == "bonusAlphabetCompleted":
                        logger.info("Processed game update: {}", update)
                        if update[1] == self.my_pid:
                            self.searcher.confirm_bonus()
            # We are given the bomb, so we should submit a word
            if self.my_pid == self.bomb_pid and self.my_ready:
                word = self.searcher.search(self.bomb_syllable)
                if word is not None:
                    logger.info(
                        "Typing word '{}' for syllable '{}'", word, self.bomb_syllable
                    )
                    if self.human:
                        time.sleep(1.5 * random.random() + 0.5)
                        for c in word + Keys.RETURN:
                            time.sleep(random.random() * 0.07)
                            actions = ActionChains(self.game.driver)
                            actions.send_keys(c)
                            actions.perform()
                    else:
                        actions = ActionChains(self.game.driver)
                        actions.send_keys(word + Keys.RETURN)
                        actions.perform()
                    self.my_ready = False
                else:
                    logger.warning(
                        "No words left for syllable '{}'!", self.bomb_syllable
                    )
