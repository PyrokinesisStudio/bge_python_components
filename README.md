# BGE Python Components
A small Blender addon to provide UI-configurable Python components. Designed to support Python components outside of Moguri's component branch (such as UPBGE's implementation).

The addon will ensure that the relevant scripts are stored inside the text blocks of the '.blend' file, but they can be safely edited without being overwritten.

## Why use components?
Components provide better encapsulation support out-of-the-box than Python controllers. For scripts that run every frame, they remove the boilerplate required. They also provide a user-friendly interface for configuration (and support a greater number of data types than the native BGE logic bricks). 

NB, this system takes control over the mainloop to remove the requirement for the user to explictly update the components. Components are updated __after__ logic bricks.
