import subprocess
import sys

result = subprocess.run([
    'ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null',
    'raspberry@192.168.11.26',
    'python3', '-c', '''
import sqlite3
db = "/home/raspberry/temperature_monitoring/temperature_server/data/temperature.db"
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM temperature_readings WHERE sensor_id LIKE \\"%%TEST%%\\"")
count = c.fetchone()[0]
print(f"削除対象: {count}件")
if count > 0:
    c.execute("DELETE FROM temperature_readings WHERE sensor_id LIKE \\"%%TEST%%\\"")
    conn.commit()
    print("✓ 削除完了")
conn.close()
'''
], capture_output=True, text=True)

print(result.stdout)
if result.stderr:
    print('Error:', result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
