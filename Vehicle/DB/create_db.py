from .database import db
from .models import *

def get_all_models():
    return BaseModel.__subclasses__()

def init(reset=False):
    db.connect(reuse_if_open=True)
    all_models = get_all_models()
    if reset:
        db.drop_tables(all_models, safe=True)
    db.create_tables(all_models, safe=True)

if __name__ == '__main__':
    init(reset = True)

