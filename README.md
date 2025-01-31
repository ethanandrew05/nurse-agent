# AI Nurse Agent

An intelligent system that captures medical conversations, transcribes them, analyzes the content, and automatically fills out EPIC documentation.

## Features

- Real-time audio capture and transcription
- Medical terminology-aware speech recognition
- Natural Language Processing for medical context understanding
- Automated EPIC documentation filling
- HIPAA-compliant security measures

## Project Structure

```
nurse-agent/
├── src/
│   ├── audio/      # Audio capture and transcription
│   ├── nlp/        # Natural Language Processing
│   ├── epic/       # EPIC integration
│   ├── api/        # FastAPI endpoints
│   └── utils/      # Utility functions
├── tests/          # Test files
└── requirements.txt
```

## Setup

1. Create and activate the conda environment:
```bash
conda create -n nurse_agent python=3.10
conda activate nurse_agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install additional system dependencies:
```bash
# For macOS
brew install portaudio

# For Ubuntu/Debian
sudo apt-get install python3-pyaudio
```

## Development

More details about development setup and contribution guidelines will be added as the project progresses.

## Security and Compliance

This project is designed with HIPAA compliance in mind. All patient data is encrypted and handled according to healthcare security standards.

## License

[License details to be added] 