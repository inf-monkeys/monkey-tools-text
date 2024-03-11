import os
import subprocess
from paddleocr import PaddleOCR, PPStructure


class OCRHelper:
    def __init__(self, language="ch"):
        self.language = language
        self.ocr = PaddleOCR(
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
            lang=self.language,
        )
        self.structure = PPStructure(show_log=False, lang=self.language)

    def preprocess(self, img_path: str):
        # 图像预处理
        try:
            result = self.ocr.ocr(img_path, cls=True)
        except Exception as e:
            raise Exception(f"OCR 识别失败: {e}")

        # 提取识别结果
        extracted_texts = []
        for item in result:
            for text_block in item:
                text = text_block[1][0]
                extracted_texts.append(text)

        text = "\n".join(extracted_texts)
        return text

    def recognize_text(self, img_path: str, task_id: str):
        save_folder = "tmp/" + task_id + "/docx/"
        # 检查 docx 文件夹是否存在
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)
        # 版面恢复
        cmd = [
            "paddleocr",
            "--image_dir",
            img_path,
            "--type",
            "structure",
            "--recovery",
            "true",
            "--use_pdf2docx_api",
            "true",
            "--output",
            save_folder,
        ]
        print("识别文本：", ' '.join(cmd))
        # 
        try:
            result = subprocess.run(cmd, shell=False, check=True)
            if result.returncode == 0:
                print(f"版面识别成功，docx 文件地址为 {save_folder}")
                return save_folder + os.listdir(save_folder)[0]
        except subprocess.CalledProcessError as e:
            print(f"版面恢复（PPStructure）失败，错误信息为 {e}")
            raise Exception("版面恢复失败")
        return None

    def table_structure(self, img_path: str):
        save_folder = "tmp/" + os.path.basename(img_path).split('.')[0] + "/xlsx/"
        cmd = [
            "paddleocr",
            "--image_dir",
            img_path,
            "--type",
            "table_structure",
            "--layout",
            "false",
            "--output",
            save_folder,
        ]
        # TODO 提取 output 所有 .xlsx 文件
