# path = r"TICBRNO-MALY_OFICIAL-EN-WEB.pdf"
import time

path = r"../test_pdfs/this-is-designer-pieces-from-brno.pdf"

import fitz

doc = fitz.open(path)
text = ""
for page in doc:
    if page.number == 0 or page.get_text() == '' or len(page.get_text()) < 800:
        continue
    if page.number == len(doc) - 1:
        break
    lowercase_count = sum(1 for char in page.get_text() if char.islower())
    if len(page.get_text()) / lowercase_count < 2:
        text += page.get_text()

num_lines = 0
lines = text.split('\n')
lines_cnt = len(lines)
i = 0
curr_line = ''
while i < lines_cnt:

    while lines[i].isdigit() and i < lines_cnt - 1:
        num_lines += 1
        i += 1
    if 0 < num_lines <= 2:
        num_lines = 0
    if num_lines > 2:
        del lines[i - num_lines:i]
        lines_cnt -= num_lines
        i -= num_lines
        num_lines = 0
    if curr_line == lines[i]:
        del lines[i]
        del lines[i - 1]
        lines_cnt -= 2
        i -= 2
    else:
        curr_line = lines[i]
    i += 1

print('---------------------------------------------')
# make text from lines
text = '\n'.join(lines)
print(text)
print('---------------------------------------------')
