# coding: utf-8
# Run a test server.
from app import app

import sys
if sys.version_info.major < 3:
    reload(sys)
sys.setdefaultencoding('utf8')

app.run(host='0.0.0.0', port=8080, debug=True)
