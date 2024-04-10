@echo off
REM Create a new directory for the build files
if not exist build (
    mkdir build
)
cd build

REM Run CMake to generate the build files
cmake -G "Visual Studio 16 2019" -A x64 ..

cd ..

REM Build the project
"C:/Program Files (x86)/Microsoft Visual Studio/2019/Community/MSBuild/Current/Bin/MSBuild.exe" bws_cef.sln /p:Configuration=Release /m
