from flask import current_app
import os

# to store utility functions

def calculate_total_holding(full_stock_information={}):
    
    all_holdings = []
    
    for stock in full_stock_information:
        all_holdings.append(stock['amount'] * stock['share'])
    
    return sum(all_holdings)


def find_value_in_object(objects, key, value):

    for obj in objects:
        if obj.get(key) == value:
            return obj
    return None


def remove_duplicates(dictionaries):
    seen = set()
    unique_dictionaries = []

    for d in dictionaries:
        # Convert the dictionary to a frozenset to make it hashable
        frozen_dict = frozenset(d.items())

        if frozen_dict not in seen:
            seen.add(frozen_dict)
            unique_dictionaries.append(d)

    return unique_dictionaries


def clear_tmp_profile_dir():

    folder_path = current_app.config['UPLOAD_FOLDER']
    
    for item in os.listdir(folder_path):
        if item != "do_not_delete_me.txt":
            item_path = os.path.join(folder_path, item)

            # Check if it's a file, and remove it
            if os.path.isfile(item_path):
                os.remove(item_path)


