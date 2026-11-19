import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

class DatabaseUtil:

  def __init__(self):
    self.db_config = os.getenv("DB_URI")

    try:
      self.connection = psycopg2.connect(self.db_config)
    except Exception as e:
      print(f"Error connecting to database: {e}")
      self.connection = None

  def schema_details(self, schema_name):

    schema_info_context = ''
           
    connection = self.connection
    cursor = connection.cursor()
    schema_info_context = f"Database Schema: {schema_name}\n"

    try:
      cursor.execute("SELECT TABLE_NAME from information_schema.tables where table_schema = %s;", (schema_name,))
      tables_list = cursor.fetchall()
      
      for table in tables_list:
        table_name = table[0]
        schema_info_context =f"{schema_info_context}\nTable: {table_name}\n"
      
        cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s;", (table_name,))
        columns_list = cursor.fetchall()
      
        for column in columns_list:
          column_name = column[0]
          data_type = column[1]
          schema_info_context=f"{schema_info_context} Column: {column_name}, Data Type: {data_type}\n" 
      
        cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;") 
        sample_data = cursor.fetchall()
        schema_info_context = f"{schema_info_context} Sample Data: \n"
        for row in sample_data:
          schema_info_context=f"{schema_info_context}     {row}\n"

    except Exception as e:
      print(f"Error fetching schema details: {e}")
      schema_info_context=f"Error fetching schema details: {e}"
    finally:
      if cursor:
        cursor.close()
      if connection:
        connection.close()
    return schema_info_context


  def execute_query(self, query):
    try:
      connection = self.connection
      cursor = connection.cursor()
      cursor.execute(query)
      result = cursor.fetchall()
      connection.commit()
      return str(result)
    except Exception as e:
      print(f"Error executing query: {e}")
      return None
    finally: 
      if cursor:
        cursor.close()
      if connection:
        connection.close()







# obj = DatabaseUtil(os.getenv("DB_URI"))

# result = obj.schema_details('public')

# with open("text_schema_details.txt", "w") as f:
#   f.write(result)