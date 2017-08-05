import wxt520
import requests

if __name__ == '__main__':
    wxt = wxt520.WXT520('/dev/ttyUSB1', address='0', timeout=10)

    while 1:
        line = wxt.readline()
        if line:
            data = wxt520.WXT520.message_to_dict(line)
	    data[data['Type']] = data.pop('Data')
	    print data
            r = requests.post('http://localhost:9001/api/', json=data)
            if r.status_code != 200:
                print 'Received error %d' % r.status_code
                print r.headers
                print r.text
