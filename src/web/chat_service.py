import os
from groq import Groq

class ChatService:
    def __init__(self):
        self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.conversation_history = [
            {
                "role": "system",
                "content": """You are an AI medical assistant helping healthcare professionals. 
                You have access to patient records and can help answer questions about the patient's 
                medical history, current condition, and treatment plans. Always maintain a professional 
                and clinical tone, and be sure to reference relevant patient information when appropriate."""
            }
        ]

    def send_message(self, message, patient_context=None):
        try:
            # If patient context is provided, add it to the message
            if patient_context:
                context_message = {
                    "role": "system",
                    "content": f"""Current patient information:
                    Name: {patient_context.get('firstName')} {patient_context.get('lastName')}
                    Age: {patient_context.get('age')}
                    Gender: {patient_context.get('gender')}
                    Current Symptoms: {patient_context.get('symptoms')}
                    Vital Signs: {patient_context.get('vitalSigns')}
                    Medications: {patient_context.get('medications')}
                    Allergies: {patient_context.get('allergies')}
                    Medical History: {patient_context.get('medicalHistory')}
                    Family History: {patient_context.get('familyHistory')}
                    Current Diagnosis: {patient_context.get('diagnosis')}
                    Treatment Plan: {patient_context.get('treatmentPlan')}
                    Notes: {patient_context.get('notes')}"""
                }
                self.conversation_history.append(context_message)

            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "content": message
            })

            # Get completion from Groq API
            completion = self.client.chat.completions.create(
                messages=self.conversation_history,
                model="llama-3.3-70b-versatile",
                temperature=0.5
            )

            # Add assistant's response to history
            if completion.choices[0].message.content:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": completion.choices[0].message.content
                })

            return completion.choices[0].message.content

        except Exception as e:
            print(f"Error in chat service: {e}")
            raise e

    def clear_history(self):
        self.conversation_history = [{
            "role": "system",
            "content": "You are an AI medical assistant helping healthcare professionals."
        }] 