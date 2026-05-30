from bagels.models.split import Split
from bagels.models.database.app import Session


def create_split(data):
    session = Session()
    try:
        new_split = Split(**data)
        session.add(new_split)
        session.commit()
        session.refresh(new_split)
        session.expunge(new_split)
        return new_split
    finally:
        session.close()


def get_splits_by_record_id(record_id):
    session = Session()
    try:
        return session.query(Split).filter_by(recordId=record_id).all()
    finally:
        session.close()


def get_split_by_id(split_id):
    session = Session()
    try:
        return session.query(Split).get(split_id)
    finally:
        session.close()


def update_split(split_id, updated_data):
    session = Session()
    try:
        split = session.query(Split).get(split_id)
        if split:
            for key, value in updated_data.items():
                setattr(split, key, value)
            session.commit()
        return split
    finally:
        session.close()


def delete_split(split_id):
    session = Session()
    try:
        split = session.query(Split).get(split_id)
        if split:
            session.delete(split)
            session.commit()
        return split
    finally:
        session.close()


def delete_splits_by_record_id(record_id):
    session = Session()
    try:
        session.query(Split).filter_by(recordId=record_id).delete()
        session.commit()
    finally:
        session.close()
