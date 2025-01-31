# -*- coding: utf-8 -*-
# @place: Pudong, Shanghai
# @file: data_processor.py
# @time: 2023/7/22 11:31
import datetime
from elasticsearch import helpers
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from langchain.text_splitter import RecursiveCharacterTextSplitter
import sys
sys.path.append("/Users/zhangyinhan1/Desktop/code/rag_project/llm_4_doc_qa")
from utils.db_client import milvus_client
from utils.db_client import es_client
from common.llm_chat_api import get_text_embedding
from utils.logger import logger
from data_process.file_parser import FileParser
from config.config_parser import EMBEDDING_MODEL


# 数据处理
class DataProcessor(object):
    def __init__(self, file_path, file_content=""):
        self.file_path = file_path
        self.file_content = file_content

    def text_loader(self):
        logger.info(f'loading file: {self.file_path}')
        documents, file_type = FileParser(self.file_path, self.file_content).parse()
        return documents, file_type

    @staticmethod
    def text_spliter(documents):
        # 接下来，我们将文档拆分成块。
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=0)
        texts = text_splitter.split_documents(documents)
        return texts

    @staticmethod
    def text_embedding(texts):
        _ids = []
        sources = []
        contents = []
        embeddings = []
        for i, text in enumerate(texts):
            source = text.metadata['source']
            content = text.page_content
            content = content.replace('\n', '')
            embedding = get_text_embedding(content, EMBEDDING_MODEL)
            _ids.append(i + 1)
            sources.append(source)
            contents.append(content)
            embeddings.append(embedding)
            logger.info(f'source: {source}, got text {i} embedding...')
        datas = [_ids, sources, contents, embeddings]
        return datas

    @staticmethod
    def es_data_insert(datas):
        if datas:
            action = ({
                "_index": "docs",
                # "_type": "_doc",
                "_source": {
                    "source": datas[1][i],  # sources
                    "cont_id": datas[0][i], # _ids
                    "content": datas[2][i], # contents
                    "insert_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            } for i in range(len(datas[0])))
            helpers.bulk(es_client, action)
            logger.info("insert data to es")
        else:
            logger.info("no insert data!")

    @staticmethod
    def milvus_data_insert(datas):
        insert_result = milvus_client.insert(datas)
        milvus_client.flush()
        # 将collection加载至内存
        milvus_client.load()
        logger.info(f"insert data to milvus, {insert_result}")

    def data_insert(self):
        documents, file_type = self.text_loader()
        texts = self.text_spliter(documents)
        datas = self.text_embedding(texts)
        # print(datas)
        self.es_data_insert(datas)
        self.milvus_data_insert(datas)


if __name__ == '__main__':
    DataProcessor(file_path='../files/demo.txt').data_insert()