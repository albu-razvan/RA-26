FROM --platform=linux/amd64 ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Thank you, Gemini, for this beautiful list of dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget git python2 \
    # Core X11 & Legacy Toolkits
    libx11-6 libxext6 libxrender1 libxtst6 libxi6 libxt6 libxaw7 libxmu6 libxpm4 \
    # 3D/OpenGL (Fixes the OGRE error and swrast error)
    libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa libosmesa6 freeglut3 \
    # Fonts and Audio
    libfreetype6 libfontconfig1 libasound2 \
    # GLib and GNOME basics
    libglib2.0-0 libsm6 libice6 libdbus-1-3 libxss1 libxkbfile1 \
    # Qt5 / XCB / Modern GUI needs
    libnss3 libnspr4 libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 \
    libxkbcommon-x11-0 \
    # Avahi/mDNS (Optional, but stops those "Daemon not running" warnings)
    avahi-daemon libavahi-client3 \
    && rm -rf /var/lib/apt/lists/*

COPY ./software /software
WORKDIR /software

RUN tar -xzf pynaoqi.tar.gz && rm pynaoqi.tar.gz && \
    tar -xzf choregraphe.tar.gz && rm choregraphe.tar.gz && \
    tar -xzf robot-settings.tar.gz && rm robot-settings.tar.gz

RUN mv choregraphe-2.8.8-ubuntu2204 choregraphe && \
    mv robot-settings_linux64_1.2.1-6c3a1204f_20210902-182550 robot-settings

ENV PYTHONPATH=/software/pynaoqi-python2.7-2.8.7.4-linux64-20210819_141148/lib/python2.7/site-packages:${PYTHONPATH}
ENV PATH=/software/choregraphe/bin:/software/robot-settings/bin:${PATH}

ENV LD_LIBRARY_PATH=/software/choregraphe/lib:/software/robot-settings/lib:${LD_LIBRARY_PATH}

# Force software rendering to avoid GPU driver mismatches
ENV LIBGL_ALWAYS_SOFTWARE=1

# Force Qt to avoid OpenGL (maybe?)
ENV QT_QUICK_BACKEND=software
ENV QT_XCB_GL_INTEGRATION=none
ENV QT_OPENGL=software

# Remove older bundled libz
# This forces the app to use the modern system version of libz.so.1
RUN rm -f /software/choregraphe/lib/libz.so.1 /software/robot-settings/lib/libz.so.1

RUN chmod +x /software/choregraphe/bin/choregraphe-bin \
             /software/robot-settings/bin/robot_settings

WORKDIR /workspace

CMD ["bash"]