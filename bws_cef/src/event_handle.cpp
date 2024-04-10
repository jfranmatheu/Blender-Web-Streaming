#include <iostream>
#include <string>
#include <thread>
#include <cef_app.h>
#include <cef_client.h>
#include <cef_render_handler.h>
#include <boost/interprocess/shared_memory_object.hpp>
#include <boost/interprocess/mapped_region.hpp>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>


void event_handling_loop(int sock, CefRefPtr<CefBrowser> browser) {
    char buffer[1024];
    while (true) {
        // Receive a line from the server.
        std::string line;
        while (true) {
            ssize_t len = recv(sock, buffer, sizeof(buffer) - 1, 0);
            if (len <= 0) {
                return;
            }
            buffer[len] = 0;
            line += buffer;
            if (!line.empty() && line.back() == '\n') {
                line.pop_back();
                break;
            }
        }

        // Split the line into commands.
        std::istringstream iss(line);
        std::vector<std::string> commands((std::istream_iterator<std::string>(iss)), std::istream_iterator<std::string>());

        // Handle the commands.
        if (commands[0] == "mousemove") {
            int x = std::stoi(commands[1]);
            int y = std::stoi(commands[2]);
            CefMouseEvent event;
            event.x = x;
            event.y = y;
            browser->GetHost()->SendMouseMoveEvent(event, false);
        } else if (commands[0] == "click") {
            int x = std::stoi(commands[1]);
            int y = std::stoi(commands[2]);
            bool mouse_up = std::stoi(commands[3]);
            CefBrowserHost::MouseButtonType button_type = commands[4] == "left" ? MBT_LEFT : MBT_RIGHT;
            CefMouseEvent event;
            event.x = x;
            event.y = y;
            browser->GetHost()->SendMouseClickEvent(event, button_type, mouse_up, 1);
        } else if (commands[0] == "resize") {
            int width = std::stoi(commands[1]);
            int height = std::stoi(commands[2]);
            // Resize the browser.
        } else if (commands[0] == "scroll") {
            int x = std::stoi(commands[1]);
            int y = std::stoi(commands[2]);
            int delta_y = std::stoi(commands[3]);
            CefMouseEvent event;
            event.x = x;
            event.y = y;
            browser->GetHost()->SendMouseWheelEvent(event, 0, delta_y);
        } else if (commands[0] == "unicode") {
            bool key_down = std::stoi(commands[1]);
            int character = std::stoi(commands[2]);
            int windows_key_code = std::stoi(commands[3]);
            int modifiers = std::stoi(commands[4]);
            CefKeyEvent event;
            event.type = key_down ? KEYEVENT_RAWKEYDOWN : KEYEVENT_KEYUP;
            event.windows_key_code = windows_key_code;
            event.character = character;
            event.modifiers = modifiers;
            browser->GetHost()->SendKeyEvent(event);
        } else if (commands[0] == "@") {
            if (commands[1] == "KILL") {
                // Exit the application.
                CefQuitMessageLoop();
                return;
            }
        }
    }
}