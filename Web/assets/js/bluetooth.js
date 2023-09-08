window.commandList = []

function webBleConnect (service) {
    return new Promise(async resolve => {
        await service.getCharacteristic(UUID.PREFIX + UUID.CUSTOM_INFO_COUNT)
            .then(characteristic => characteristic.readValue())
            .then(i => i.buffer)
            .then(window.ab2str)
            .then(parseInt)
            .then(value => {
            console.log('custom-info-count ' + value)
            that.customInfoCount = value
            })
        await service.getCharacteristic(UUID.PREFIX + UUID.CUSTOM_COMMAND_COUNT)
            .then(characteristic => characteristic.readValue())
            .then(i => i.buffer)
            .then(window.ab2str)
            .then(parseInt)
            .then(value => {
            console.log('custom-command-count ' + value)
            that.customCommandCount = value
            })
        let customInfoList = []
        for (let index = 0; index < that.customInfoCount; index++) {
            let ending = (index + 1).toString(16)
            ending = '0'.repeat(4 - ending.length) + ending
            customInfoList.push(UUID.PREFIX + UUID.CUSTOM_INFO + ending)
            customInfoList.push(UUID.PREFIX + UUID.CUSTOM_INFO_LABEL + ending)
        }
        let customCommandList = []
        for (let index = 0; index < that.customCommandCount; index++) {
            let ending = (index + 1).toString(16)
            ending = '0'.repeat(4 - ending.length) + ending
            customCommandList.push(UUID.PREFIX + UUID.CUSTOM_COMMAND_LABEL + ending)
        }
        resolve(Promise.all([
            service.getCharacteristic(UUID.SERVICE_NAME),
            service.getCharacteristic(UUID.DEVICE_MODEL),
            service.getCharacteristic(UUID.WIFI_NAME),
            service.getCharacteristic(UUID.IP_ADDRESS),
            service.getCharacteristic(UUID.NOTIFY_MESSAGE),
            service.getCharacteristic(UUID.INPUT_SEP),
            service.getCharacteristic(UUID.CUSTOM_COMMAND_INPUT),
            service.getCharacteristic(UUID.CUSTOM_COMMAND_NOTIFY),
            ...customInfoList.map(i => service.getCharacteristic(i)),
            ...customCommandList.map(i => service.getCharacteristic(i))
    ]))
    })
}


function subscribeCharacteristic (uuid) {
    return new Promise(async resolve => {
      window.getCharacteristic(uuid).addEventListener('characteristicvaluechanged', event => {
        if (event.target.uuid === UUID.NOTIFY_MESSAGE) {
          let msg = window.ab2str(event.target.value.buffer)
          const h = window.$createElement
          window.$notify({
            title: 'Error',
            message: h('i', { style: 'color: teal'}, msg)
          })
        } else if (event.target.uuid === UUID.CUSTOM_COMMAND_NOTIFY) {
          let msg = window.ab2str(event.target.value.buffer)
          if (window.commandOutputShouldRefresh) {
            window.commandOutputShouldRefresh = false
            window.commandOutput = ''
          }
          let output = window.commandOutput + msg
          if (output.endsWith('&#&')) {
            output = output.replace('&#&', '')
            window.commandOutputShouldRefresh = true
          }
          window.commandOutput = output
        } else {
          let value = window.ab2str(event.target.value.buffer)
          let char = window.infoList.find(i => i.uuid === uuid)
          let char_label = window.infoList.find(i => i.uuid_label === uuid)
          if (char) {
            char.value = value
          }
          if (char_label) {
            char_label.label = value
          }
        }
      })
      await window.getCharacteristic(uuid).startNotifications()
      resolve()
    })
}

function getCharacteristic (uuid) {
    return this.characteristicsList.find(i => i.uuid === uuid)
}

function readInfoCharacteristic (uuid) {
    return new Promise(resolve => {
        window.getCharacteristic(uuid).readValue()
        .then(i => i.buffer)
        .then(window.ab2str)
        .then((value) => {
            let char = window.infoList.find(i => i.uuid === uuid)
            let char_label = window.infoList.find(i => i.uuid_label === uuid)
            if (char) {
            char.value = value
            }
            if (char_label) {
            char_label.label = value
            }
            resolve()
        })
    })
}


window.isIphone = navigator.userAgent.indexOf('iPhone') > -1 || navigator.userAgent.indexOf('iphone') > -1
isAndroid = navigator.userAgent.indexOf('Android') > -1 || navigator.userAgent.indexOf('Adr') > -1


function connectBluetoothInstructor() {
    window.navigator.bluetooth.
        requestDevice({
            filters: [{
                services: [window.UUID.SERVICE_ID]
            }]
        })
        .then(device => {
            window.device = device
            return device.gatt.connect()
        })
        .then(server => {
            window.serverId = server.device.id
            return server.getPrimaryService(UUID.SERVICE_ID)
        })
        .then(service => {
            if (isIphone) {
                console.log('ios webBLE')
                return webBleConnect(service)
            } else {
                return service.getCharacteristics()
            }
        })
        .then(characteristics => {
            window.characteristicsList = characteristics
            window.isConnected = true
            document.querySelector('#bt-btn').disabled = true
            whileConnected()
              .then(showBtModal)
        })
        .catch(console.log)
} 

async function whileConnected () {
      console.log('Connected!')

      window.infoList = []
      window.infoList.push({
        preset: true,
        uuid: '',
        label: 'Device ID',
        value: window.serverId
      })
      window.infoList.push({
        preset: true,
        uuid: UUID.DEVICE_MODEL,
        label: 'Model',
        value: ' '
      })
      window.infoList.push({
        preset: true,
        uuid: UUID.WIFI_NAME,
        label: 'Wifi',
        value: '...'
      })
      window.infoList.push({
        preset: true,
        uuid: UUID.IP_ADDRESS,
        label: 'IP Address',
        value: '...'
      })

      await window.subscribeCharacteristic(UUID.WIFI_NAME)
      await window.subscribeCharacteristic(UUID.IP_ADDRESS)
      await window.readInfoCharacteristic(UUID.DEVICE_MODEL)
      await window.subscribeCharacteristic(UUID.NOTIFY_MESSAGE)
      await window.subscribeCharacteristic(UUID.CUSTOM_COMMAND_NOTIFY)
      
      window.characteristicsList.filter(i => i.uuid.indexOf(UUID.CUSTOM_INFO_LABEL) >= 0).map(item => {
        window.infoList.push({
          uuid: item.uuid.replace(UUID.CUSTOM_INFO_LABEL, UUID.CUSTOM_INFO),
          uuid_label: item.uuid,
          label: '-',
          value: ''
        })
      })
      for (let i = 0; i < window.infoList.length; i++) {
        if (window.infoList[i].preset) continue
        await window.readInfoCharacteristic(window.infoList[i].uuid_label)
        await window.subscribeCharacteristic(window.infoList[i].uuid)
      }
      window.characteristicsList.filter(i => i.uuid.indexOf(UUID.CUSTOM_COMMAND_LABEL) >= 0).map(item => {
        window.commandList.push({
          uuid: item.uuid,
          label: '...'
        })
      })
      for (let i = 0; i < window.commandList.length; i++) {
        await window.readCommandLabel(window.commandList[i].uuid)
      }
    
}


function readCommandLabel (uuid) {
    return new Promise(resolve => {
      window.getCharacteristic(uuid).readValue()
        .then(i => i.buffer)
        .then(window.ab2str)
        .then((label) => {
          window.commandList.find(i => i.uuid === uuid).label = label
          resolve()
        })
    })
}

function inputWifi () {
    let key = 'pisugar'
    let ssid = JSON.stringify({course: window.course})
    let password = ""
    
    let sendArray = window.str2abs(`${key}%&%${ssid}%&%${password}&#&`)
    window.sendSeparately(sendArray, UUID.INPUT_SEP)

    document.querySelector('#bt-take-image').innerText = 'Request Sent'
    document.querySelector('#bt-take-image').disabled = true

}


function sendCommand (uuid) {
    let sendArray = window.str2abs(`${window.key}%&%${uuid.slice(-4)}&#&`)
    window.sendSeparately(sendArray, UUID.CUSTOM_COMMAND_INPUT)
}


async function sendSeparately (array, uuid) {
    for (const i in array) {
      await window.getCharacteristic(uuid).writeValue(array[i])
      await window.wait(0.4)
    }
}


async function wait (sec) {
    return new Promise((resolve => {
      setTimeout(() => {
        resolve(true)
      }, 1000 * sec)
    }))
}


function str2abs(str) {
    let val = ''
    for (let i = 0; i < str.length; i++) {
      if (val === '') {
        val = str.charCodeAt(i).toString(16)
      } else {
        val += ',' + str.charCodeAt(i).toString(16)
      }
    }
    let valArray = val.split(',')
    let bufferArray = []
    while (valArray.length > 0) {
      let value = valArray.splice(0, 20).join(',')
      bufferArray.push(new Uint8Array(value.match(/[\da-f]{2}/gi).map(function (h) {
        return parseInt(h, 16)
      })).buffer)
    }
    return bufferArray
}

function ab2str (buf) {
    return String.fromCharCode.apply(null, new Uint8Array(buf));
}


function showBtModal() {
  document.querySelector('#btModalLabel').innerText += window.infoList[1].value
  window.btModal = new bootstrap.Modal(document.getElementById('btModal'), {})

  if(window.data.is_instructor) document.querySelector('#bt-instructor-modal').style.display = 'block'
  else document.querySelector('#bt-student-modal').style.display = 'block'
  document.querySelector('#bt-network-status').innerHTML = `<b>Network Status:</b> ${window.infoList[2].value}`


  setInterval(() => {
    document.querySelector('#bt-take-image').disabled = !window.infoList[2].value || window.infoList[2].value == 'Not available'  ? true : false
    document.querySelector('#bt-network-status').innerHTML = `<b>Network Status:</b> ${window.infoList[2].value}`
  }, 1000);

  btModal.show()
}

function disconnect() {
  if(!window.device) return;
  if(window.device.gatt.connected) window.device.gatt.disconnect()
  console.log("Disconnected")

  setTimeout(() => {
    document.querySelector('#bt-btn').disabled = false
    document.querySelector('#btModalLabel').innerText = "Connected to ";
    document.querySelector('#bt-instructor-modal').style.display = 'none'
    document.querySelector('#bt-student-modal').style.display = 'none'
    document.querySelector('#bt-take-image').innerText = 'Activate'
    document.querySelector('#bt-take-image').disabled = false

  }, 200);

  window.btModal.hide()
  window.btModal = undefined

}



