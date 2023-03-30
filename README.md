# Ective BLE
Small python script that connects to your Ective Bluetooth battery and reports the transmitted values to the cli.
## Install
Use Python, PIP and venv to install the packages in the `requirements.txt`.

## Usage
Run with the MAC address of your battery.

```bash
$ python3 ectiveBms.py -v -d EE:EE:EE:EE:EE:EE
```
Receive results in stdout :tada:

```json
{
  "soc": 99,
  "volt": 13.297,
  "current": -0.744,
  "cap": 200.0,
  "cycles": 8,
  "temp": 14.8
}
```
