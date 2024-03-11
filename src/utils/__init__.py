import string, random, os


def generate_random_string(length):
    # Define the characters that can be used in the random string
    characters = string.ascii_letters + string.digits

    # Generate a random string of specified length
    random_string = ''.join(random.choice(characters) for _ in range(length))

    return random_string


def ensure_directory_exists(dir_path):
    """
        如果目录不存在则创建目录
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
    return dir_path
