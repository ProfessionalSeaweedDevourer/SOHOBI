from datetime import datetime
from uuid import uuid4


class FablefileManager:
    @staticmethod
    async def fileUpload(folder, file, mode, maxSize):
        try:
            content = await file.read()
            if len(content) > maxSize:
                return "fail"  # 파일용량 (바이트 단위)
            filename = file.filename
            type = filename[-5:]
            filename = filename.replace(type, "")

            if mode == "uuid":
                filename = filename + "_" + str(uuid4()) + type
            elif mode == "date":
                now = datetime.today()
                now = datetime.strftime(now, "%Y%m%d%H%M%S")
                filename = filename + "_" + now + type

            f = open(folder + filename, "wb")
            f.write(content)
            f.close()

            return filename
        except:
            return "fail"
