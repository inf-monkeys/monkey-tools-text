import json
import os
import subprocess
import uuid

from .app import api, app
from flask_restx import Resource
from flask import request
from langchain_community.document_loaders import UnstructuredURLLoader, SeleniumURLLoader
from paddleocr import PaddleOCR
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter, CharacterTextSplitter

from ..oss import oss_client
from ..utils import generate_random_string, ensure_directory_exists
from ..utils.file_convert_helper import FileConvertHelper
from ..utils.ocr_helper import OCRHelper

text_ns = api.namespace('text', description='Text operations')


@text_ns.route('/extract-url-content')
class ExtractUrlContent(Resource):
    @text_ns.doc('extract_url_content')
    @text_ns.vendor({
        "x-monkey-tool-name": "extract_url_content",
        "x-monkey-tool-categories": ["file"],
        "x-monkey-tool-display-name": "URL 文本提取",
        "x-monkey-tool-description": "从 URL 中提取 HTML 内容",
        "x-monkey-tool-icon": "emoji:📝:#56b4a2",
        "x-monkey-tool-extra": {
            "estimateTime": 30,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "启用 Headless Browser",
                "name": "headless",
                "type": "boolean",
                "default": "",
                "required": True,
            },
            {
                "displayName": "URL",
                "name": "url",
                "type": "string",
                "default": "",
                "required": True,
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "提取结果",
                "type": "string",
                "properties": [
                    {
                        "name": "metadata",
                        "displayName": "元数据",
                        "type": "any",
                    },
                    {
                        "name": "page_content",
                        "displayName": "文本内容",
                        "type": "string",
                    },
                ],
                "typeOptions": {
                    "multipleValues": True
                }
            },
        ],
    })
    def post(self):
        input_data = request.json
        url = input_data.get("url")
        headless = input_data.get("headless")
        try:
            if url is None:
                raise Exception("URL 不能为空")
            if headless:
                loader = UnstructuredURLLoader(urls=[url])
            else:
                loader = SeleniumURLLoader(urls=[url])
            document = loader.load()
            result = {}
            for doc in document:
                result["metadata"] = doc.metadata
                result["page_content"] = doc.page_content
            # FIX 不能直接返回 json 数据，否则 conductor 序列化会报错
            return {
                "result": result,
            }
        except Exception as e:
            raise Exception(f"提取 URL 中的文本失败: {e}")


@text_ns.route("/file-convert")
class FileConvert(Resource):
    @text_ns.doc('file_convert')
    @text_ns.vendor({
        "x-monkey-tool-name": "file_convert",
        "x-monkey-tool-categories": ["file"],
        "x-monkey-tool-display-name": "文件格式转换",
        "x-monkey-tool-description": "对文件格式进行转换",
        "x-monkey-tool-icon": "emoji:📝:#56b4a2",
        "x-monkey-tool-extra": {
            "estimateTime": 10,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "文件 URL",
                "name": "url",
                "type": "file",
                "default": "",
                "required": True,
                "typeOptions": {
                    "multipleValues": False,
                    "accept": ".png,.jpg,.pdf,.docx,.xlsx,.csv,.md",
                    "maxSize": 1024 * 1024 * 20
                }
            },
            {
                "displayName": "输入格式",
                "name": "input_format",
                "type": "options",
                "default": "PNG",
                "required": True,
                "options": [
                    {
                        "name": "PNG",
                        "value": "png",
                    },
                    {
                        "name": "JPG",
                        "value": "jpg",
                    },
                    {
                        "name": "PDF",
                        "value": "pdf",
                    },
                    {
                        "name": "DOCX",
                        "value": "docx",
                    },
                    {
                        "name": "XLSX",
                        "value": "xlsx",
                    },
                    {
                        "name": "CSV",
                        "value": "csv",
                    },
                    {
                        "name": "MD",
                        "value": "md",
                    },
                ],
            },
            {
                "displayName": "输出格式",
                "name": "output_format",
                "type": "options",
                "default": "",
                "required": True,
                "options": [
                    {
                        "name": "PNG",
                        "value": "png",
                    },
                    {
                        "name": "JPG",
                        "value": "jpg",
                    },
                ],
                "displayOptions": {
                    "show": {
                        "input_format": ["jpg", "png"],
                    }
                },
            },
            {
                "displayName": "输出格式",
                "name": "output_format",
                "type": "options",
                "default": "",
                "required": True,
                "options": [
                    {
                        "name": "PDF",
                        "value": "pdf",
                    },
                    {
                        "name": "DOCX",
                        "value": "docx",
                    },
                    {
                        "name": "Markdown",
                        "value": "md",
                    },
                ],
                "displayOptions": {
                    "show": {
                        "input_format": ["pdf", "docx", "md"],
                    }
                },
            },
            {
                "displayName": "输出格式",
                "name": "output_format",
                "type": "options",
                "default": "",
                "required": True,
                "options": [
                    {
                        "name": "XLSX",
                        "value": "xlsx",
                    },
                    {
                        "name": "CSV",
                        "value": "csv",
                    },
                ],
                "displayOptions": {
                    "show": {
                        "input_format": ["xlsx", "csv"],
                    }
                },
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "转换后结果的 URL",
                "type": "any",
            },
        ],
    })
    def post(self):
        input_data = request.json
        url = input_data.get("url")
        helper = FileConvertHelper(url)
        input_format = input_data.get("input_format")
        output_format = input_data.get("output_format")

        # 1. 将文件下载到本地
        task_id = generate_random_string(20)
        input_file = helper.download_file(url, "tmp/" + task_id)

        # 2. 根据 input_format 调用helper
        if input_format == "png" or input_format == "jpg":
            output_file = input_file + "." + output_format
            helper.convert_image(input_file, output_file, output_format)
        elif input_format == "pdf" and output_format == "docx":
            output_file = input_file + "." + output_format
            helper.pdf_to_docx(input_file, output_file)
        elif input_format == "docx" and output_format == "md":
            output_file = input_file + "." + output_format
            helper.docx_to_markdown(input_file, output_file)
        elif input_format == "pdf" and output_format == "md":
            output_file = input_file + "." + output_format
            helper.pdf_to_markdown(input_file, output_file)
        elif input_format == "xlsx" and output_format == "csv":
            output_file = input_file + "." + output_format
            helper.xlsx_to_csv(input_file, output_file)
        elif input_format == "csv" and output_format == "xlsx":
            output_file = input_file + "." + output_format
            helper.csv_to_xlsx(input_file, output_file)
        else:
            raise Exception("不支持的格式转换")
        # 3. 将文件上传到 OSS
        url = oss_client.upload_file_tos(output_file, key=f"workflow/artifact/{task_id}/{output_file.split('/')[-1]}")
        print("txt_url", url)
        # 4. 返回文件 URL
        return {
            "result": url,
        }


@text_ns.route("/ocr")
class OCR(Resource):
    @text_ns.doc('ocr')
    @text_ns.vendor({
        "x-monkey-tool-name": "ocr",
        "x-monkey-tool-categories": ["file"],
        "x-monkey-tool-display-name": "OCR 识别",
        "x-monkey-tool-description": "使用 OCR 进行识别",
        "x-monkey-tool-icon": "emoji:📝:#56b4a2",
        "x-monkey-tool-extra": {
            "estimateTime": 20,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "图片 URL",
                "name": "url",
                "type": "file",
                "default": "",
                "required": True,
                "typeOptions": {
                    "multipleValues": False,
                    "accept": ".jpg,.jpeg,.png",
                    "maxSize": 1024 * 1024 * 20
                }
            }
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "识别结果 TXT",
                "type": "string",
            },
        ],
    })
    def post(self):
        input_data = request.json
        image_url = input_data.get("url")
        tmp_file_folder = ensure_directory_exists("./download")
        image_file_name = oss_client.download_file(image_url, tmp_file_folder)

        ocr = PaddleOCR(
            # 检测模型
            # det_model_dir='{your_det_model_dir}',
            # # 识别模型
            # rec_model_dir='{your_rec_model_dir}',
            # # 识别模型字典
            # rec_char_dict_path='{your_rec_char_dict_path}',
            # # 分类模型
            # cls_model_dir='{your_cls_model_dir}',
            # 加载分类模型
            use_angle_cls=True,
            lang='ch',
        )
        result = ocr.ocr(image_file_name, cls=True)
        extracted_texts = []
        for item in result:
            for text_block in item:
                text = text_block[1][0]
                extracted_texts.append(text)
        text = "\n".join(extracted_texts)

        print(text)
        return {"result": text}


@text_ns.route("/pdf-to-text")
class OCR(Resource):
    @text_ns.doc('pdf_to_txt')
    @text_ns.vendor({
        "x-monkey-tool-name": "pdf_to_txt",
        "x-monkey-tool-categories": ["file"],
        "x-monkey-tool-display-name": "PDF 文本提取",
        "x-monkey-tool-description": "从 PDF 提取纯文本",
        "x-monkey-tool-icon": "emoji:📝:#56b4a2",
        "x-monkey-tool-extra": {
            "estimateTime": 180,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "PDF 文件链接",
                "name": "pdfUrl",
                "type": "file",
                "default": "",
                "required": True,
                "typeOptions": {
                    "multipleValues": False,
                    "accept": ".pdf",
                    "maxSize": 1024 * 1024 * 20
                }
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "txt 文件链接",
                "type": "string",
            },
        ],
    })
    def post(self):
        input_data = request.json
        print(input_data)
        task_id = generate_random_string(20)
        folder = ensure_directory_exists(f"./download/{task_id}")
        pdf_folder = ensure_directory_exists(f"./download/{task_id}/pdf")
        docx_folder = ensure_directory_exists(f"./download/{task_id}/docx")
        md_folder = ensure_directory_exists(f"./download/{task_id}/md")
        txt_folder = ensure_directory_exists(f"./download/{task_id}/txt")
        pdfUrl = input_data.get("pdfUrl")
        if not pdfUrl:
            raise Exception("任务参数中不存在 pdfUrl")
        pdf_file = oss_client.download_file(pdfUrl, pdf_folder)
        pdf_name = pdf_file.split("/")[-1]

        # pdf to docx
        cmd = [
            "paddleocr",
            "--image_dir",
            pdf_file,
            "--type",
            "structure",
            "--recovery",
            "true",
            "--use_pdf2docx_api",
            "true",
            "--output",
            docx_folder,
        ]
        try:
            result = subprocess.run(cmd, shell=False, check=True)
            if result.returncode == 0:
                print(f"版面识别成功，docx 文件地址为 {docx_folder}")
        except subprocess.CalledProcessError as e:
            print(f"版面识别失败，错误信息为 {e}")
            raise Exception("版面识别失败")

        docx_path = f"{docx_folder}/{pdf_name.replace('.pdf', '.docx')}"
        md_path = f"{md_folder}/{pdf_name.replace('.pdf', '.md')}"
        cmd = [
            "pandoc",
            "-s",
            docx_path,
            "--wrap=none",
            "--reference-links",
            "-t",
            "markdown",
            "-o",
            md_path,
        ]
        try:
            result = subprocess.run(cmd, shell=False, check=True)
            if result.returncode == 0:
                print(f"pandoc 转换成功，转换之后的 Markdown 文件地址为 {md_path}")
        except subprocess.CalledProcessError as e:
            print(f"pandoc 转换失败，错误信息为 {e}")
            raise Exception("pandoc 转换失败")

        txt_path = f"{txt_folder}/{pdf_name.replace('.pdf', '.txt')}"
        cmd = [
            "pandoc",
            md_path,
            "-o",
            txt_path,
        ]
        try:
            result = subprocess.run(cmd, shell=False, check=True)
            if result.returncode == 0:
                print(f"pandoc 转换成功，转换之后的 txt 文件地址为 {txt_path}")
        except subprocess.CalledProcessError as e:
            print(f"pandoc 转换失败，错误信息为 {e}")
            raise Exception("pandoc 转换失败")

        url = oss_client.upload_file_tos(txt_path, f"workflow/artifact/{task_id}/{uuid.uuid4()}.txt")

        return {"result": url}


@text_ns.route("/pp-structure")
class PPStructure(Resource):
    @text_ns.doc('pp_structure')
    @text_ns.vendor({
        "x-monkey-tool-name": "pp_structure",
        "x-monkey-tool-categories": ["file"],
        "x-monkey-tool-display-name": "版面恢复",
        "x-monkey-tool-description": "对复杂文档进行分析和处理",
        "x-monkey-tool-icon": "emoji:📝:#56b4a2",
        "x-monkey-tool-extra": {
            "estimateTime": 60,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "文件 URL",
                "name": "url",
                "type": "file",
                "default": "",
                "required": True,
                "typeOptions": {
                    "multipleValues": False,
                    "accept": ".jpg,.jpeg,.png",
                    "maxSize": 1024 * 1024 * 20
                }
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "文档 URL",
                "type": "string",
            },
        ],
    })
    def post(self):
        input_data = request.json
        print(input_data)
        url = input_data.get("url")
        task_id = generate_random_string(20)
        folder = ensure_directory_exists(f"./download/{task_id}")
        input_file = oss_client.download_file(url, folder)
        ocr_helper = OCRHelper()
        try:
            result = ocr_helper.recognize_text(img_path=str(input_file), task_id=task_id)
            if result is None:
                raise Exception("版面恢复失败")
            # 上传 docx 文件到 OSS
            file_url = oss_client.upload_file_tos(result, key=f"workflow/artifact/{task_id}/{result.split('/')[-1]}")
            return {
                "result": file_url,
            }
        except Exception as e:
            raise Exception(f"版面恢复失败: {e}")


@text_ns.route("/text-combination")
class TextCombination(Resource):
    @text_ns.doc('text_combination')
    @text_ns.vendor({
        "x-monkey-tool-name": "text_combination",
        "x-monkey-tool-categories": ["text"],
        "x-monkey-tool-display-name": "文本合并",
        "x-monkey-tool-description": "文本合并",
        "x-monkey-tool-icon": "emoji:✂️:#f3cd5f",
        "x-monkey-tool-extra": {
            "estimateTime": 30,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "文档类型",
                "name": "textOrUrl",
                "type": "options",
                "default": "text",
                "required": False,
                "options": [
                    {"name": "纯文本内容", "value": "text"},
                    {"name": "文本链接", "value": "url"},
                ],
            },
            {
                "displayName": "需要合并的文档列表（支持JSON，JSONL，TXT）",
                "name": "documents",
                "type": "string",
                "default": [],
                "required": False,
                "displayOptions": {"show": {"textOrUrl": ["text"]}},
                "typeOptions": {
                    "multipleValues": True
                }
            },
            {
                "displayName": "需要合并的文档 URL 列表（支持JSON，JSONL，TXT）",
                "name": "documentsUrl",
                "type": "file",
                "default": [],
                "required": False,
                "displayOptions": {"show": {"textOrUrl": ["url"]}},
                "typeOptions": {
                    "multipleValues": True,
                    "accept": ".json,.jsonl,.txt",
                    "maxSize": 1024 * 1024 * 20
                }
            },
            {
                "displayName": "文本格式",
                "name": "documentType",
                "type": "options",
                "options": [
                    {
                        "name": "JSON",
                        "value": "json",
                    },
                    {
                        "name": "JSONL",
                        "value": "jsonl",
                    },
                    {
                        "name": "TXT",
                        "value": "txt",
                    },
                ],
                "default": "txt",
                "required": True,
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "合并后的输出的文本URL",
                "type": "string",
            },
        ],
    })
    def post(self):
        input_data = request.json
        task_id = generate_random_string(20)
        documents = input_data.get("documents")
        documents_url = input_data.get("documentsUrl")
        if isinstance(documents_url, str):
            documents_url = [documents_url]
        document_type = input_data.get("documentType")  # 支持 json，jsonl, txt

        if not documents and not documents_url:
            raise Exception("参数错误：未提供文档")
        if document_type not in ["json", "jsonl", "txt"]:
            raise Exception("参数错误：不支持的文档类型")

        folder = ensure_directory_exists(f"./download/text_combination/{task_id}")
        # 合并本地文件
        if len(documents) > 1:
            document_list = []
            for document in documents:
                if document_type == "json":
                    document_list.append(json.load(document))
                elif document_type == "jsonl":
                    for line in document.split("\n"):
                        document_list.append(json.loads(line))
                elif document_type == "txt":
                    document_list.append(document)

            filename = f"{folder}/all.{document_type}"
            with open(filename, "w") as f:
                if document_type == "json":
                    json.dump(document_list, f)
                elif document_type == "jsonl":
                    for document in document_list:
                        f.write(json.dumps(document))
                        f.write("\n")
                elif document_type == "txt":
                    for document in document_list:
                        f.write(f"{document}")
                        f.write("\n")
            url = oss_client.upload_file_tos(filename, f"workflow/artifact/{task_id}/result.txt")
            return {"result": url}
        else:
            # 下载需要合并的文件到本地
            for document_url in documents_url:
                oss_client.download_file(document_url, folder)
                print(f"{len(documents_url)}个文件下载完成，开始合并")
            all_document_file = os.listdir(folder)
            document_list = []
            document = documents[0]
            if document_type == "json":
                document_list.append(json.load(document))
            elif document_type == "jsonl":
                for line in document.split("\n"):
                    document_list.append(json.loads(line))
            elif document_type == "txt":
                document_list.append(document)

            for document_file in all_document_file:
                file_ext = document_file.split(".")[-1]
                file_name = f"{folder}/{document_file}"
                if file_ext != document_type:
                    raise Exception(f"配置的文档类型为 {document_type}，但是实际上文档类型为 {file_ext}")
                if document_type == "json":
                    with open(file_name, "r") as f:
                        document_list.append(json.load(f))
                elif document_type == "jsonl":
                    with open(file_name, "r") as f:
                        for line in f.readlines():
                            document_list.append(json.loads(line))
                elif document_type == "txt":
                    with open(file_name, "r") as f:
                        document_list.append(f.read())
            all_filename = f"{folder}/all.{document_type}"
            print(all_filename, document_type)
            with open(all_filename, "w") as f:
                if document_type == "json":
                    json.dump(document_list, f)
                elif document_type == "jsonl":
                    for document in document_list:
                        f.write(json.dumps(document))
                        f.write("\n")
                elif document_type == "txt":
                    for document in document_list:
                        f.write(document)
                        f.write("\n")
            url = oss_client.upload_file_tos(
                all_filename, f"workflow/artifact/{task_id}/result.{document_type}"
            )
            return {"result": url}


@text_ns.route("/text-replace")
class TextReplace(Resource):
    @text_ns.doc('text_replace')
    @text_ns.vendor({
        "x-monkey-tool-name": "text_replace",
        "x-monkey-tool-categories": ["text"],
        "x-monkey-tool-display-name": "文本替换",
        "x-monkey-tool-description": "将文档指定内容替换为另一内容，返回新的文档 URL",
        "x-monkey-tool-icon": "emoji:✂️:#f3cd5f",
        "x-monkey-tool-extra": {
            "estimateTime": 30,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "文档类型",
                "name": "documentType",
                "type": "options",
                "default": "document",
                "options": [
                    {
                        "name": "纯文本",
                        "value": "document",
                    },
                    {
                        "name": "文本 URL",
                        "value": "documentUrl",
                    },
                ],
                "required": True,
            },
            {
                "displayName": "文档文本",
                "name": "document",
                "type": "string",
                "default": "",
                "required": False,
                "displayOptions": {
                    "show": {
                        "documentType": ["document"],
                    },
                },
            },
            {
                "displayName": "文档 URL",
                "name": "documentUrl",
                "type": "file",
                "default": "",
                "required": False,
                "displayOptions": {
                    "show": {
                        "documentType": ["documentUrl"],
                    },
                },
                "typeOptions": {
                    "multipleValues": False,
                    "accept": ".txt",
                    "maxSize": 1024 * 1024 * 20
                }
            },
            {
                "displayName": "在文档中搜索的文本",
                "name": "searchText",
                "type": "string",
                "default": "",
                "required": True,
            },
            {
                "displayName": "替换搜索结果的文本",
                "name": "replaceText",
                "type": "string",
                "default": "",
                "required": True,
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "替换后的文档或文档 URL",
                "type": "string",
            },
        ],
    })
    def post(self):
        input_data = request.json
        print(input_data)
        task_id = generate_random_string(20)

        document_type = input_data.get("documentType")
        if document_type == "document":
            input_data.pop("documentUrl")
        elif document_type == "documentUrl":
            input_data.pop("document")

        text = input_data.get("searchText")
        replace_text = input_data.get("replaceText")
        document = input_data.get("document")
        document_url = input_data.get("documentUrl")
        if not text or (not document and not document_url):
            raise Exception("参数错误")

        if document:
            document = document.replace(text, replace_text)
            return {"result": document}
        elif document_url:
            tmp_file_folder = ensure_directory_exists("./download")
            file_name = oss_client.download_file(document_url, tmp_file_folder)
            with open(file_name, "r") as f:
                lines = f.readlines()
            lines = [line.replace(text, replace_text) for line in lines]
            with open(file_name, "w") as f:
                for line in lines:
                    f.write(line)
            url = oss_client.upload_file_tos(file_name, f"workflow/artifact/{task_id}/result.txt")
            return {"result": url}


@text_ns.route("/text-segment")
class TextSegmentResource(Resource):
    @text_ns.doc('text_segment')
    @text_ns.vendor({
        "x-monkey-tool-name": "text_segment",
        "x-monkey-tool-categories": ["text"],
        "x-monkey-tool-display-name": "长文本分段",
        "x-monkey-tool-description": "根据不同类型的文件进行文本分段，返回新的文档 URL",
        "x-monkey-tool-icon": "emoji:✂️:#f3cd5f",
        "x-monkey-tool-extra": {
            "estimateTime": 30,
        },
        "x-monkey-tool-input": [
            {
                "displayName": "txt 文件",
                "name": "txtUrl",
                "type": "file",
                "default": "",
                "required": True,
                "typeOptions": {
                    "multipleValues": False,
                    "accept": ".txt",
                    "maxSize": 1024 * 1024 * 20
                }
            },
            {
                "displayName": "切割器",
                "name": "splitType",
                "type": "options",
                "default": "splitByCharacter",
                "options": [
                    {
                        "name": "字符切割器",
                        "value": "splitByCharacter",
                        "description": "字符切割器",
                    },
                    {
                        "name": "代码切割器",
                        "value": "splitCode",
                        "description": "代码切割器",
                    },
                    {
                        "name": "Markdown 切割器",
                        "value": "markdown",
                        "description": "Markdown 切割器",
                    },
                    {
                        "name": "递归字符切割器",
                        "value": "recursivelySplitByCharacter",
                        "description": "递归字符切割器",
                    },
                    {
                        "name": "Token 切割器",
                        "value": "splitByToken",
                        "description": "Token 切割器",
                    },
                ],
                "required": False,
            },
            {
                "displayName": "块大小",
                "name": "chunkSize",
                "type": "number",
                "default": 2000,
                "required": True,
            },
            {
                "displayName": "块重叠",
                "name": "chunkOverlap",
                "type": "number",
                "default": 10,
                "required": True,
            },
            {
                "displayName": "分割符",
                "name": "separator",
                "type": "string",
                "default": "\n\n",
                "required": False,
                "displayOptions": {
                    "show": {
                        "splitType": [
                            "splitByCharacter",
                            "recursivelySplitByCharacter",
                        ],
                    },
                },
            },
            {
                "displayName": "语言",
                "name": "language",
                "type": "options",
                "default": "python",
                "displayOptions": {
                    "show": {
                        "splitType": ["splitCode"],
                    },
                },
                "options": [
                    {
                        "name": "cpp",
                        "value": "cpp",
                    },
                    {
                        "name": "go",
                        "value": "go",
                    },
                    {
                        "name": "java",
                        "value": "java",
                    },
                    {
                        "name": "js",
                        "value": "js",
                    },
                    {
                        "name": "php",
                        "value": "php",
                    },
                    {
                        "name": "proto",
                        "value": "proto",
                    },
                    {
                        "name": "python",
                        "value": "python",
                    },
                    {
                        "name": "rst",
                        "value": "rst",
                    },
                    {
                        "name": "ruby",
                        "value": "ruby",
                    },
                    {
                        "name": "rust",
                        "value": "rust",
                    },
                    {
                        "name": "scala",
                        "value": "scala",
                    },
                    {
                        "name": "swift",
                        "value": "swift",
                    },
                    {
                        "name": "markdown",
                        "value": "markdown",
                    },
                    {
                        "name": "latex",
                        "value": "latex",
                    },
                    {
                        "name": "html",
                        "value": "html",
                    },
                    {
                        "name": "sol",
                        "value": "sol",
                    },
                ],
                "required": True,
            },
        ],
        "x-monkey-tool-output": [
            {
                "name": "result",
                "displayName": "分段后的文本列表",
                "type": "string",
                "typeOptions": {
                    "multipleValues": True
                }
            },
        ],
    })
    def post(self):
        input_data = request.json
        chunk_size = input_data.get("chunkSize")
        chunk_overlap = input_data.get("chunkOverlap")
        language = input_data.get("language")
        txt_url = input_data.get("txtUrl")
        separator = input_data.get("separator")
        split_type = input_data.get("splitType")
        print(input_data)
        if not txt_url or not split_type or not chunk_size or not chunk_overlap:
            raise Exception("参数错误")

        tmp_file_folder = ensure_directory_exists("./download")
        txt_file_name = oss_client.download_file(txt_url, tmp_file_folder)

        text = ""
        try:
            with open(txt_file_name, "r", encoding="utf-8") as f:
                text = f.read()
        except:
            raise Exception("读取文件失败，请传入合法的 utf-8 格式的 txt 文件")

        splitter = None
        if split_type == "splitByCharacter":
            splitter = CharacterTextSplitter(
                separator=separator,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        elif split_type == "splitCode":
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        elif split_type == "markdown":
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        elif split_type == "recursivelySplitByCharacter":
            splitter = RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)
        elif split_type == "splitByToken":
            splitter = CharacterTextSplitter.from_tiktoken_encoder(
                chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )
        else:
            raise Exception(f"split_type 参数错误")

        segments = splitter.split_text(text)
        print("转换完成")
        return {"result": segments}
