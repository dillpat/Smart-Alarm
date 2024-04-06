## Smart Alarm Clock

This is a Python application that serves as a smart alarm clock, incorporating features like setting alarms, canceling alarms, displaying weather information, fetching news headlines, and notifying users through text-to-speech or audible sound.

### Prerequisites

- Python 3.x
- Flask
- requests
- pyttsx3

### Installation

1. Clone this repository to your local machine.
2. Install dependencies using `pip install -r requirements.txt`.
3. Run the application using `python smart_alarm_clock.py`.
4. Access the application through a web browser at `http://localhost:5000`.

### Usage

#### Setting Alarms

- Navigate to `/alarm?alarm=Set` endpoint.
- Choose the desired alarm time and provide an optional message.
- Click the "Set Alarm" button.

#### Canceling Alarms

- Navigate to `/alarm?alarm=Cancel` endpoint.
- Select the alarm you want to cancel from the list.
- Click the "Cancel Alarm" button.

#### Viewing Current Time and Notifications

- Access the `/time_feed` endpoint to view the current time and a list of past notifications.

### Configuration

The application uses a `config.json` file for configuration. Modify this file to adjust settings such as API keys, logging configurations, and file paths.

### Contributing

Contributions are welcome! Please fork the repository, make your changes, and submit a pull request.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
