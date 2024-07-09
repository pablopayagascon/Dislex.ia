from PIL import Image
import os
from textblob import TextBlob
import language_tool_python
import requests
import pandas as pd
import random
import speech_recognition as sr
import pyttsx3
import time
import eng_to_ipa as ipa

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

import time

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''


def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''


# image to text API authentication
subscription_key_imagetotext = "**************"
endpoint_imagetotext = "https://dislexia.cognitiveservices.azure.com/"
computervision_client = ComputerVisionClient(
    endpoint_imagetotext, CognitiveServicesCredentials(subscription_key_imagetotext))

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# text correction API authentication
api_key_textcorrection = "************"
endpoint_textcorrection = "https://api.bing.microsoft.com/v7.0/SpellCheck"

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

my_tool = language_tool_python.LanguageTool('en-US')

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# method for extracting the text


def image_to_text(path):
    read_image = open(path, "rb")
    read_response = computervision_client.read_in_stream(read_image, raw=True)
    read_operation_location = read_response.headers["Operation-Location"]
    operation_id = read_operation_location.split("/")[-1]

    while True:
        read_result = computervision_client.get_read_result(operation_id)
        if read_result.status.lower() not in ['notstarted', 'running']:
            break
        time.sleep(5)

    text = []
    if read_result.status == OperationStatusCodes.succeeded:
        for text_result in read_result.analyze_result.read_results:
            for line in text_result.lines:
                text.append(line.text)

    return " ".join(text)

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# method for finding the spelling accuracy


def spelling_accuracy(extracted_text):
    spell_corrected = TextBlob(extracted_text).correct()
    return ((len(extracted_text) - (levenshtein(extracted_text, spell_corrected)))/(len(extracted_text)+1))*100

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# method for gramatical accuracy


def gramatical_accuracy(extracted_text):
    spell_corrected = TextBlob(extracted_text).correct()
    if not spell_corrected:
        return "N/A 3"  # Devuelve 3 si el texto corregido está vacío
    try:
        correct_text = my_tool.correct(spell_corrected)
        extracted_text_set = set(spell_corrected.split(" "))
        correct_text_set = set(correct_text.split(" "))
        n = max(len(extracted_text_set - correct_text_set),
                len(correct_text_set - extracted_text_set))
        return ((len(spell_corrected) - n)/(len(spell_corrected)+1))*100
    except language_tool_python.utils.LanguageToolError as e:
        print(f"Error en la verificación gramatical: {str(e)}")
        return "N/A 2"  # Devuelve 2 si hay un error en la verificación gramatical

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''

# percentage of corrections


def percentage_of_corrections(extracted_text):
    data = {'text': extracted_text}
    params = {
        'mkt': 'en-us',
        'mode': 'proof'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Ocp-Apim-Subscription-Key': api_key_textcorrection,
    }
    response = requests.post(endpoint_textcorrection,
                             headers=headers, params=params, data=data)
    json_response = response.json()
    
    # Comprobar si 'flaggedTokens' está en la respuesta
    if 'flaggedTokens' in json_response:
        return len(json_response['flaggedTokens']) / len(extracted_text.split(" ")) * 100
    else:
        print("Respuesta del API no contiene 'flaggedTokens'")
        return "N/A"  # 4 cualquier otro valor por defecto que consideres apropiado

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''


# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''


def get_feature_array(path: str):
    feature_array = []
    extracted_text = image_to_text(path)
    feature_array.append(spelling_accuracy(extracted_text))
    feature_array.append(gramatical_accuracy(extracted_text))
    feature_array.append(percentage_of_corrections(extracted_text))
    return feature_array

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''


def generate_csv(folder: str, label: int, csv_name: str):
    arr = []
    for image in os.listdir(folder):
        path = os.path.join(folder, image)
        feature_array = get_feature_array(path)
        feature_array.append(label)
        # print(feature_array)
        arr.append(feature_array)
        print(feature_array)
    print(arr)
    pd.DataFrame(arr, columns=["spelling_accuracy", "gramatical_accuracy", " percentage_of_corrections", "presence_of_dyslexia"]).to_csv(csv_name + ".csv")

# '''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''


def score(input):
    if input[0] <= 96.40350723266602:
        var0 = [0.0, 1.0]
    else:
        if input[1] <= 99.1046028137207:
            var0 = [0.0, 1.0]
        else:
            if input[2] <= 2.408450722694397:
                if input[2] <= 1.7936508059501648:
                    var0 = [1.0, 0.0]
                else:
                    var0 = [0.0, 1.0]
            else:
                var0 = [1.0, 0.0]
    return var0


#'''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''
from PIL import Image

def recortar_imagenes_en_carpeta(carpeta):
    for filename in os.listdir(carpeta):
        if filename.endswith(".jpg") or filename.endswith(".png"):  # Filtrar solo archivos de imagen
            path_imagen = os.path.join(carpeta, filename)
            try:
                imagen = Image.open(path_imagen)

                # Dimensiones de la imagen original
                ancho_original, alto_original = imagen.size

                # Coordenadas para el recorte
                left = 0
                upper = alto_original - 1060
                right = ancho_original
                lower = alto_original

                # Recortar la imagen
                imagen_recortada = imagen.crop((left, upper, right, lower))

                # Guardar la imagen recortada (sobrescribir la original)
                imagen_recortada.save(path_imagen)

                print(f"Imagen recortada y guardada: {filename}")

            except Exception as e:
                print(f"Error al procesar la imagen {filename}: {str(e)}")


#'''-------------------------------------------------------------------------------------------------------------------------------------------------------------------------'''
# generate_csv(r'C:\Users\pablo\OneDrive\Documentos\GitHub\Sistemas interactivos UI\data\dyslexic', 1, "dislexia")
# generate_csv(r'C:\Users\pablo\OneDrive\Documentos\GitHub\Sistemas interactivos UI\data\non_dyslexic', 0, "no-dislexia")
# generate_csv(r'C:\Users\pablo\OneDrive\Documentos\GitHub\Sistemas interactivos UI\model_training\hsf_1', 0, "test-mix-dislexia")
# recortar_imagenes_en_carpeta(r'C:\Users\pablo\OneDrive\Documentos\GitHub\Sistemas interactivos UI\model_training\hsf_1')
