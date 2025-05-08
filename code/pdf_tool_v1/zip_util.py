import zipfile
from uuid import uuid4
import os

def zip_csvs(paths):
    zip_name = f"outputs/{uuid4().hex}_csvs.zip"
    with zipfile.ZipFile(zip_name, 'w') as z:
        for path in paths:
            z.write(path, os.path.basename(path))
    return zip_name