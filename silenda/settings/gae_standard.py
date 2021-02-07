from silenda.settings.base import *

STATIC_URL = '/static/'

import pymysql
pymysql.version_info = (1, 4, 6, 'final', 0)
pymysql.install_as_MySQLdb()
