package main

import (
	"github.com/energye/energy"
	"os"
	"runtime"
)

func main() {
	runtime.LockOSThread()

	// Inicializar CEF.
	energy.Initialize()

	// Crear una ventana de navegador.
	browser := energy.NewBrowser("http://www.google.com", nil)

	// Ejecutar el bucle de mensajes de la aplicación.
	energy.RunMessageLoop()

	// Limpieza y salida.
	browser.CloseBrowser(true)
	energy.Shutdown()
	os.Exit(0)
}
