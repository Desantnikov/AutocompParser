from sqlalchemy import Column, Integer, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


engine = create_engine('sqlite:///./database.db', echo=False)
Base = declarative_base()


class Query(Base):
    __tablename__ = 'queries'
    id = Column(Integer, primary_key=True)
    text = Column(String)
    autocompletions = relationship("Autocompletion", back_populates="query")
    # for each query may be 0-6 autocompletions

    def __init__(self, query):
        self.text = query

    def __repr__(self):
        return 'ID: {}; QUery: {}; Autocompletions: {};'.format(self.id, self.text, ', '.join([autocompl.text for autocompl in self.autocompletions]))


class Autocompletion(Base):
    __tablename__ = 'autocompletions'
    id = Column(Integer, primary_key=True)
    text = Column(String)
    query_id = Column(Integer, ForeignKey('queries.id'))
    query = relationship("Query", back_populates="autocompletions")

    def __init__(self, text, query_id):
        self.text = text
        self.query_id = query_id

Base.metadata.create_all(engine)