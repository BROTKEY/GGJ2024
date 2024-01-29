# GGJ2024
## Installation

Create python environment:
```shell
python3.10 -m venv venv
. venv/bin/activate
```

Install the project:
```shell
pip install -e .
```

## Usage
Launch leapmotion controller for hand tracking:
```shell
launch_leapmotion
```
Launch the game:
```shell
launch_game
```
(Optional) Launch in debug mode if you do not have a leapmotion device available:
```shell
launch_game --debug
```