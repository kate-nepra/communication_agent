import asyncio
import logging
import os
from markdown import markdown
import requests
from llama_index_client import Document
from src.constants import MAX_SIZE
from llama_parse import LlamaParse
from dotenv import load_dotenv

from src.data_acquisition.constants import logger
from src.data_acquisition.data_retrieval.constants import PDF_FOLDER

load_dotenv()


def batch_scrape_pdfs(urls: list[str]):
    return [scrape_pdf(url, PDF_FOLDER) for url in urls]


def scrape_pdf(url, destination_folder) -> str:
    """Downloads the pdf from the given url and saves it to the destination folder"""
    destination = destination_folder + '/' + url.split('/')[-1]
    response = requests.get(url)
    with open(destination, 'wb') as file:
        file.write(response.content)
    return destination


class PdfProcessor:

    def __init__(self, urls: list[str]):
        self.urls = urls
        self.destinations = batch_scrape_pdfs(urls) if urls else []

    def get_cleaned_md(self, text) -> str:
        """Removes empty lines, lines with only numbers, and duplicate lines from the markdown file. Also removes lines
        that contain only 'NO_CONTENT_HERE' string. Returns the cleaned markdown as a string."""
        num_lines = 0
        lines = text.split('\n')
        lines_cnt = len(lines)
        i = 0
        curr_line = ''
        while i < lines_cnt:
            line = lines[i]
            alphabet_character_count = sum(c.isalpha() for c in line)
            if alphabet_character_count == 0 or lines[i] == 'NO_CONTENT_HERE':
                del lines[i]
                lines_cnt -= 1
                continue
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
            i, curr_line, lines, lines_cnt = self._remove_duplicate_line(curr_line, i, lines, lines_cnt)
            i += 1

        text = '\n'.join(lines)
        return text

    @staticmethod
    def _remove_duplicate_line(curr_line, i, lines, lines_cnt):
        """Removes duplicate lines from the markdown."""
        if curr_line == lines[i]:
            del lines[i]
            del lines[i - 1]
            lines_cnt -= 2
            i -= 2
        else:
            curr_line = lines[i]
        return i, curr_line, lines, lines_cnt

    @staticmethod
    def _split_md_into_chunks(text, max_size) -> list[str]:
        """Splits the cleaned markdown into chunks by headers, max size of a given size."""
        if len(text) < max_size:
            return [text]
        header_index = [i for i in range(len(text)) if text.startswith('##', i)]
        chunks = [text[header_index[i]:header_index[i + 1]] for i in range(len(header_index) - 1)]
        for i in range(len(chunks)):
            header = chunks[i].split('\n')[0]
            if 'map' in header.lower():
                chunks[i] = ''
            if len(chunks[i]) > max_size:
                while len(chunks[i]) > max_size:
                    last_newline = chunks[i][:max_size].rfind('\n')
                    if last_newline == -1:
                        last_whitespace = chunks[i][:max_size].rfind(' ')
                        last_newline = last_whitespace if last_whitespace != -1 else max_size
                    chunks[i] = chunks[i][last_newline:]
                    chunks.append(chunks[i][:last_newline])
        return [chunk for chunk in chunks if len(chunk) > 100]

    def _parse_pdf(self) -> Document:
        """Parses the pdf using LlamaParse and returns the first document as a markdown string."""
        documents = LlamaParse(result_type="markdown").load_data(self.destinations[0])
        return documents[0]

    async def _parse_pdfs(self) -> list[Document]:
        """Parses the pdfs using LlamaParse and returns the documents as a list of markdown strings."""
        parser = LlamaParse(result_type="markdown")
        documents = await parser.aload_data(self.destinations)
        return documents

    def get_md(self) -> str:
        """Returns the markdown string of the parsed pdf."""
        return self._parse_pdf().text

    def get_mds(self) -> list[str]:
        """Returns the markdown strings of the parsed pdfs."""
        docs = asyncio.run(self._parse_pdfs())
        return [doc.text for doc in docs]

    def get_chunks(self) -> tuple[list[str], str]:
        """Returns the chunks of the parsed pdf. If the parsed pdf is larger than MAX_SIZE, it will be split into chunks
        by headers. If the chunks are still larger than MAX_SIZE, they will be split into smaller chunks."""
        return self._split_md_into_chunks(self.get_cleaned_md(self.get_md()), MAX_SIZE), self.urls[0]

    def get_chunks_batch(self) -> tuple[list[str], str]:
        """Returns the chunks of the parsed pdfs. If the parsed pdf is larger than MAX_SIZE, it will be split into chunks
        by headers. If the chunks are still larger than MAX_SIZE, they will be split into smaller chunks."""
        mds = [self.get_cleaned_md(md) for md in self.get_mds()]
        for i in range(len(self.urls)):
            md = mds[i]
            yield self._split_md_into_chunks(md, MAX_SIZE), self.urls[i]

    def process_pdfs_from_folder(self, folder_path: str) -> tuple[list[str], str]:
        """Downloads the pdfs from the given folder and processes them."""
        file_paths = [folder_path + '/' + file for file in os.listdir(folder_path)]
        for file_path in file_paths:
            try:
                return self.process_pdf_from_path(file_path)
            except Exception as e:
                logger.error(f"Error processing pdf from path: {file_path}. Error: {e}")

    def process_pdf_from_path(self, path: str) -> tuple[list[str], str]:
        """Processes the pdf from the given path."""
        self.destinations = [path]
        self.urls = [path.split('/')[-1]]
        logger.info(f"Processing pdf: {path}")
        return self.get_chunks()
