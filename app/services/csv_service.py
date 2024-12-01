import csv
import os

def read_users_from_csv(csv_file_path):
    if not os.path.exists(csv_file_path):
        return []

    users = []
    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            users.append(row)
    return users

def write_user_to_csv(csv_file_path, user_data_to_save):
    if not os.path.exists(csv_file_path):
        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=user_data_to_save.keys())
            writer.writeheader()
            writer.writerow(user_data_to_save)
    else:
        with open(csv_file_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=user_data_to_save.keys())
            writer.writerow(user_data_to_save)

def update_user_in_csv(csv_file_path, user_data):
    users = []
    updated = False

    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["uuid"] == user_data["uuid"]:
                row.update(user_data)
                updated = True
            users.append(row)

    if updated:
        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(users)
    else:
        raise ValueError("User not found")

def delete_user_from_csv(csv_file_path, user_uuid):
    users = []
    row_deleted = False

    with open(csv_file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["uuid"] != user_uuid:
                users.append(row)
            else:
                row_deleted = True

    if row_deleted:
        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(users)
    else:
        raise ValueError("User not found")