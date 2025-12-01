"""Script pour mettre à jour les outputs du projet dans MongoDB"""
from pymongo import MongoClient
import json
import os

client = MongoClient('mongodb://mongodb:27017')
db = client['youtube_pipeline']

folder_name = 'video_20251130_160857'
output_dir = f'/app/output/{folder_name}'

# Lire le SEO
seo = None
seo_path = f'{output_dir}/seo.json'
if os.path.exists(seo_path):
    with open(seo_path) as f:
        seo = json.load(f)
    print(f"SEO loaded: {seo['main_video']['title'][:50]}...")

# Lister les shorts
shorts = []
shorts_dir = f'{output_dir}/shorts'
if os.path.exists(shorts_dir):
    for f in os.listdir(shorts_dir):
        if f.endswith('.mp4'):
            shorts.append({'title': f.replace('.mp4',''), 'path': f'shorts/{f}'})
print(f"Shorts found: {len(shorts)}")

# Vérifier les fichiers
illustrated = 'illustrated.mp4' if os.path.exists(f'{output_dir}/illustrated.mp4') else None
nosilence = 'nosilence.mp4' if os.path.exists(f'{output_dir}/nosilence.mp4') else None
thumbnail = 'thumbnail.png' if os.path.exists(f'{output_dir}/thumbnail.png') else None

print(f"Illustrated: {illustrated}")
print(f"Nosilence: {nosilence}")
print(f"Thumbnail: {thumbnail}")

# Mettre à jour le projet
result = db.projects.update_one(
    {'folder_name': folder_name},
    {'$set': {
        'outputs.illustrated': illustrated,
        'outputs.nosilence': nosilence,
        'outputs.thumbnail': thumbnail,
        'outputs.shorts': shorts,
        'outputs.seo': seo
    }}
)
print(f"Updated: {result.modified_count} document(s)")


