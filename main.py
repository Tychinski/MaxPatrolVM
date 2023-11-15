import json
import paramiko
import re
import psycopg2

class HostScanner:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

    def scan_and_save_to_database(self):
        os_info = self.scan()
        if os_info:
            self.write_to_postgresql(os_info)

    def scan(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            ssh.connect(self.host, username=self.username, password=self.password)

            commands = [
                "lsb_release -a",
                "uname -m",
                "cat /proc/cpuinfo"
            ]

            results = {}

            for command in commands:
                stdin, stdout, stderr = ssh.exec_command(command)
                output = stdout.read().decode()

                if "lsb_release -a" in command:
                    os_info = self.parse_os_summary(output)
                    results['distribution'] = os_info[0]
                    results['version'] = os_info[1]
                    results['architecture'] = os_info[2]
                elif "uname -m" in command:
                    results['architecture'] = output.strip()
                elif "cat /proc/cpuinfo" in command:
                    processor_info = self.parse_processor_info(output)
                    results['processor'] = processor_info

            return results

        except Exception as e:
            print(f"Ошибка сканирования {self.host}: {e}")
            return None

        finally:
            ssh.close()

    def parse_os_summary(self, output):
        distribution_id_match = re.search(r"Distributor ID:\s+(.+)", output)
        distribution_id = distribution_id_match.group(1) if distribution_id_match else "N/A"

        release_match = re.search(r"Release:\s+(.+)", output)
        release = release_match.group(1) if release_match else "N/A"

        architecture_match = re.search(r"Architecture:\s+(.+)", output)
        architecture = architecture_match.group(1) if architecture_match else "N/A"

        return distribution_id, release, architecture

    def parse_processor_info(self, output):
        processor_info = output.strip()
        return processor_info

    def write_to_postgresql(self, data):
        try:
            conn = psycopg2.connect(
                dbname="db",
                user="root",
                password="toor",
                host="192.168.47.132",
                port="5432"
            )
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS host_info (
                    id SERIAL PRIMARY KEY,
                    ip VARCHAR(15) NOT NULL,
                    distribution VARCHAR(255),
                    version VARCHAR(255),
                    architecture VARCHAR(255),
                    processor TEXT
                )
            ''')

            cursor.execute("INSERT INTO host_info (ip, distribution, version, architecture, processor) VALUES (%s, %s, %s, %s, %s)",
                           (self.host, data.get('distribution'), data.get('version'), data.get('architecture'), data.get('processor')))

            conn.commit()

            print(f"Данные записаны {self.host}.")
        except Exception as e:
            print(f"Ошибка записи в БД: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

def load_config(filename):
    try:
        with open(filename, 'r') as file:
            config = json.load(file)
        return config
    except Exception as e:
        print(f"Ошибка чтения файла с хостами: {e}")
        return None
configurations = load_config('hosts.json')

if configurations:
    for config in configurations:
        scanner = HostScanner(
            config.get("host"),
            config.get("username"),
            config.get("password")
        )
        scanner.scan_and_save_to_database()
else:
    print("Конфиг файл не найден")
