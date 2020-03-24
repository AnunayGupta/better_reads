CREATE TABLE account (
  user_id SERIAL PRIMARY KEY,
  username VARCHAR (50) UNIQUE NOT NULL,
  password VARCHAR (50) NOT NULL,
  email VARCHAR (355) UNIQUE NOT NULL,
  created_on TIMESTAMP NOT NULL,
  last_login TIMESTAMP
) ;

CREATE TABLE books (
  isbn_number VARCHAR PRIMARY KEY ,
  book_name VARCHAR NOT NULL ,
  author_name VARCHAR NOT NULL ,
  publishing_year INTEGER
) ;

CREATE TABLE reviews (
  review_id SERIAL PRIMARY KEY ,
  isbn_number VARCHAR NOT NULL REFERENCES books  ,
  reviewer_username VARCHAR NOT NULL REFERENCES account(username),
  comment VARCHAR ,
  rating INTEGER , 
  review_time TIMESTAMP
) ;
