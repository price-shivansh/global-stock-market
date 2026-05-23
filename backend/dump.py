import faulthandler
import threading
import time
import sys

faulthandler.enable()

def dump():
    time.sleep(2)
    faulthandler.dump_traceback(sys.stdout)
    print('DUMP DONE')

threading.Thread(target=dump, daemon=True).start()

import pandas
print('pandas imported')
