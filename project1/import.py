import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    f = open("books.csv")
    reader = csv.reader(f)
    next(f)
    for isbn_number,book_name,author_name,publishing_year in reader:
        publishing_year = int(publishing_year)
        db.execute("INSERT INTO books (isbn_number,book_name,author_name,publishing_year) VALUES (:isbn_number, :book_name, :author_name, :publishing_year)",
                   {"isbn_number": isbn_number, "book_name": book_name, "author_name": author_name, "publishing_year": publishing_year})
        print(f"{isbn_number} , {book_name} , {author_name} , {publishing_year}")
    db.commit()

if __name__ == "__main__":
    main()
