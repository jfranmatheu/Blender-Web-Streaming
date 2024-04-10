cmake_minimum_required(VERSION 3.10)
project(bws_cef)

set(CMAKE_CXX_STANDARD 11)

# Add CEF directories
include_directories(X:/cpp_shared_libs/cef_binary_123.0.8+g43f22da+chromium-123.0.6312.46_windows64/include)
link_directories(X:/cpp_shared_libs/cef_binary_123.0.8+g43f22da+chromium-123.0.6312.46_windows64/Release)

# Add Boost directories
include_directories(C:/local/boost_1_84_0/include)
link_directories(C:/local/boost_1_84_0/lib)

# Add source files
add_executable(bws_cef src/main.cpp)

# Link with CEF and Boost libraries
target_link_libraries(bws_cef libcef libboost_system libboost_thread)
