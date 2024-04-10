const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const robot = require('robotjs')
const net = require('net');
const WebSocket = require('ws');
const puppeteer = require('puppeteer');


/*
async function run() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  await page.goto('https://www.google.com');
  
  // simulate a user typing into an input box
  await page.type('#input-id', 'Hello World');
  
  // simulate a user clicking a button
  await page.click('#button-id');
  
  await browser.close();
}

run();
*/

const wss = new WebSocket.Server({ port: 8080 });

wss.on('connection', ws => {
  ws.on('message', message => {
    console.log(`Received message => ${message}`)
  })
  ws.send('Hello! Message From Server!!')
});


let mainWindow

const argv = require('minimist')(process.argv.slice(2));

const VIEWPORT_WIDTH = parseInt(argv.width) || 800;
const VIEWPORT_HEIGHT = parseInt(argv.height) || 600;
const SERVER_PORT = parseInt(argv['server-port']) || 1234;
const URL = argv.url || 'https://twitter.com/Blender';

let client = new net.Socket();

function createWindow () {
  mainWindow = new BrowserWindow({
    width: VIEWPORT_WIDTH,
    height: VIEWPORT_HEIGHT,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      offscreen: true
    },
    show: false
  })

  mainWindow.loadURL(URL)
  mainWindow.webContents.on('paint', (event, dirty, image) => {
    // image is a instance of NativeImage that stores the buffer of the rendering
    // you can save it or send it over IPC
    const imageData = image.toBitmap();
    client.write(imageData);
  })

  mainWindow.webContents.on('did-finish-load', () => {
    // Simulate mouse move and click
    robot.moveMouse(100, 100)
    robot.mouseClick()

    // Simulate keyboard press
    robot.keyTap('f')

    // Simulate scrolling
    robot.scrollMouse(0, 100)
  })
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit()
})

client.connect(SERVER_PORT, '127.0.0.1', function() {
    console.log('Connected to server');
});
