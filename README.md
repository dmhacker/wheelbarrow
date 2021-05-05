# wheelbarrow

<img src="https://upload.wikimedia.org/wikipedia/commons/3/37/Remotely_controlled_bomb_disposal_tool.JPG" width="277" height="208" />

wheelbarrow is a bot that plays JKLM's Bomb Party mode. The bot was designed to be somewhat intelligent:
it chooses words to maximize its bonus lives, tries to perserve words that could be useful for it to acquire more lives in the future,
and has a human mode, mimicing a human while not compromising on its ability to win games.

The name was chosen as a reference to the British [Wheelbarrow robot](https://en.wikipedia.org/wiki/Wheelbarrow_(robot)), a remote controlled device for defusing and disposing of bombs.

## Usage

wheelbarrow needs the following dependencies installed on your system:
* Python 3.8+
* Chromium v90

The bot works by spawning a Chromium browser and controlling it via Selenium.
In order to acquire Selenium and other Python dependencies, it is recommended
you first set up a virtualenv inside the top level folder after cloning like such:

```
virtualenv venv
source venv/bin/activate
```

Before running it, then install all required Python packages:

```
pip install -r requirements.txt
```

In order to run the bot, you can use the following command from the root folder:

```
python wheelbarrow <XXXX>
```

where XXXX is the 4-letter JKLM room code. By default, human mode is disabled,
making the bot type in its responses instantly. You can enable human mode
by passing in the `--human` flag.

## Limitations

These are known limitations that may or may not be addressed in the future:
* The bot only works with Chromium v90 on Linux.
* The bot can only join rooms that have been created and cannot create rooms on its own.
* If a room is not set to the Bomb Party mode, it will crash.
* It only works on English Bomb Party rooms.
* The corpus is fixed and the bot has no memory. If it encounters a word not in JKLM's dictionary, it will not persist this information
between usages. Likewise, it does not track new words that are not in the bot's current dictionary.
* The English corpus it uses is not fully expansive. There are words in JKLM that the bot is not aware of. 
