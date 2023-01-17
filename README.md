
# mediaminer_scraper
A rudimentary scraping script for fanfiction posted on mediaminer.org that converts it into epub. Originally made to help out someone because I was bored.

## Usage
This is written assuming the user knows next to nothing about Python, and so people who actually know what they are doing will probably be able to glance over it or just read the code.

First, download the file known as `MM_miner.py` from this repository and place it in the folder you want the epub saved to.

Then, create a new python file in the same folder (for this example, lets say its name is `main.py`), and write the following code in it, replacing `'https://example.url'` with the url of the main page for the story you want to download, and optionally, `'story.epub'` with the filename you want for the resulting epub. The second option can be ignored.
```
import MM_miner as MM

MM.download_story('https://example.url', save_to="story.epub")
```


Then, open the folder that contains both `main.py` and `MM_miner.py` in command prompt.
#### Ensure that the following libraries are installed:
- ebooklib
- bs4
- lxml


Then, run the command `python3 main.py`.
