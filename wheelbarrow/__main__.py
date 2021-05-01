from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

capabilities = DesiredCapabilities.CHROME
# capabilities["loggingPrefs"] = {"performance": "ALL"}  # chromedriver < ~75
capabilities["goog:loggingPrefs"] = {"performance": "ALL"}  # chromedriver 75+

driver = webdriver.Chrome(
    r"drivers/chromedriver.exe",
    desired_capabilities=capabilities,
)
driver.get("https://dmhacker.github.io")
logs = driver.get_log("performance")
print(logs)