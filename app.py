from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_mail import Mail, Message
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import logging

app = Flask(__name__)
CORS(app)

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'kartheeswarmails@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_app_password'  # Generate App Password from Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'kartheeswarmails@gmail.com'

mail = Mail(app)

# Contact Configuration
WHATSAPP_NUMBER = "+917845844982"
CONTACT_EMAIL = "kartheeswarmails@gmail.com"

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
FRUIT_MODEL_PATH = 'models/fruit_model.keras'
LEAF_MODEL_PATH = 'models/leaf_disease_model.keras'
FRUIT_MAPPING_PATH = 'mappings/fruit_classes.json'
LEAF_MAPPING_PATH = 'mappings/leaf_classes.json'
DATABASE_PATH = 'crop_disease_db.sqlite'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load models
models = {}
class_mappings = {}

def load_models():
    """Load both fruit and leaf models"""
    # Load fruit model
    try:
        models['fruit'] = load_model(FRUIT_MODEL_PATH)
        with open(FRUIT_MAPPING_PATH, 'r') as f:
            class_mappings['fruit'] = {int(k): v for k, v in json.load(f).items()}
        logger.info(f"Fruit model loaded: {len(class_mappings['fruit'])} classes")
    except Exception as e:
        logger.error(f"Error loading fruit model: {e}")
        models['fruit'] = None
        class_mappings['fruit'] = {}

    # Load leaf model
    try:
        models['leaf'] = load_model(LEAF_MODEL_PATH)
        with open(LEAF_MAPPING_PATH, 'r') as f:
            class_mappings['leaf'] = {int(k): v for k, v in json.load(f).items()}
        logger.info(f"Leaf model loaded: {len(class_mappings['leaf'])} classes")
    except Exception as e:
        logger.error(f"Error loading leaf model: {e}")
        models['leaf'] = None
        class_mappings['leaf'] = {
            0: 'Pepper__bell___Bacterial_spot',
            1: 'Pepper__bell___healthy',
            2: 'Potato___Early_blight',
            3: 'Potato___Late_blight',
            4: 'Potato___healthy',
            5: 'Tomato_Bacterial_spot',
            6: 'Tomato_Early_blight',
            7: 'Tomato_Late_blight',
            8: 'Tomato_Leaf_Mold',
            9: 'Tomato_healthy'
        }

def init_database():
    """Initialize SQLite database with backward compatibility"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if predictions table exists and what columns it has
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='predictions';")
    table_exists = cursor.fetchone()
    
    if table_exists:
        # Check existing columns
        cursor.execute("PRAGMA table_info(predictions);")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add model_type column if it doesn't exist
        if 'model_type' not in columns:
            try:
                cursor.execute('ALTER TABLE predictions ADD COLUMN model_type TEXT DEFAULT "leaf";')
                logger.info("Added model_type column to existing predictions table")
            except sqlite3.OperationalError:
                logger.info("model_type column already exists or cannot be added")
    else:
        # Create new table with all columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                model_type TEXT DEFAULT "leaf",
                predicted_class TEXT,
                confidence REAL,
                class_index INTEGER,
                filename TEXT,
                user_ip TEXT
            )
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            is_correct BOOLEAN,
            comment TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prediction_id) REFERENCES predictions (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_comprehensive_disease_info(disease_class, model_type, confidence=1.0):
    """Get comprehensive disease information with handling for both actual and generic classifications"""
    
    # Complete fruit disease database for your 4 trained classes
    fruit_diseases = {
        'Apple_Black_Rot': {
            'type': 'Fungal Disease',
            'pathogen': 'Botryosphaeria obtusa',
            'severity': 'High',
            'economic_impact': 'Can cause 20-80% yield loss if left untreated',
            'description': 'Black rot is a serious fungal disease that causes circular, brown to black lesions on apple fruits, eventually leading to complete fruit rot and mummification.',
            'symptoms': [
                'Circular brown spots on fruit surface that gradually enlarge',
                'Black rot spreading inward from wounds or stem end',
                'Concentric rings visible in advanced lesions (bull\'s-eye pattern)',
                'Fruit mummification and shriveling over time',
                'Premature fruit drop from tree branches',
                'Sweet, fermented odor emanating from infected fruits',
                'Dark, sunken lesions that become leathery in texture',
                'Secondary bacterial infections through rot wounds'
            ],
            'remedies': [
                'Apply Captan 50% WP @ 2g/L water every 10-14 days during growing season',
                'Spray Mancozeb 75% WP @ 2.5g/L water during wet weather conditions',
                'Use Propiconazole 25% EC @ 1ml/L water for systemic fungal control',
                'Apply Copper Oxychloride 50% WP @ 3g/L water as protective spray',
                'Remove and destroy all infected fruits immediately upon detection',
                'Prune dead and diseased wood during dormant winter season',
                'Apply Thiophanate-methyl @ 1g/L water for severe infections',
                'Use Ziram 76% WP @ 2g/L water as preventive measure'
            ],
            'prevention': [
                'Maintain proper orchard sanitation practices year-round',
                'Remove all mummified fruits and fallen debris regularly',
                'Prune trees for good air circulation and sunlight penetration',
                'Apply dormant season copper sprays in late winter',
                'Use disease-resistant apple varieties when replanting orchards',
                'Avoid mechanical wounds during harvest and handling operations',
                'Ensure proper storage conditions (temperature 32-40°F, humidity 85-90%)',
                'Implement integrated pest management to reduce insect wounds'
            ],
            'organic_remedies': [
                'Neem oil spray @ 5ml/L water with surfactant every 7-10 days',
                'Baking soda solution @ 5g/L water + liquid soap as foliar spray',
                'Bordeaux mixture @ 1% concentration during dormant season',
                'Compost tea application weekly during active growing season',
                'Essential oil blends (thyme, oregano) @ 2ml/L water',
                'Potassium bicarbonate @ 3g/L water for leaf and fruit treatment',
                'Milk spray @ 1:9 ratio with water (natural fungicidal properties)',
                'Diatomaceous earth dusting around tree base for prevention'
            ],
            'maintenance': [
                'Monitor orchards weekly during growing season for early symptoms',
                'Maintain proper tree nutrition with balanced fertilizer program',
                'Ensure adequate drainage around tree root zones',
                'Regular equipment sanitization with 10% bleach solution',
                'Weather monitoring for infection-favorable conditions',
                'Record keeping of all treatments and their effectiveness'
            ]
        },
        
        'Apple_Cedar_Rust': {
            'type': 'Fungal Disease',
            'pathogen': 'Gymnosporangium juniperi-virginianae',
            'severity': 'Medium to High',
            'economic_impact': 'Moderate to severe yield loss, primarily affects fruit quality and leaf health',
            'description': 'Cedar apple rust is a unique fungal disease requiring both apple trees and juniper/cedar trees to complete its complex two-host life cycle.',
            'symptoms': [
                'Bright yellow-orange spots on upper leaf surfaces in spring',
                'Circular lesions with small black dots (spermogonia) in centers',
                'Orange, tube-like projections on leaf undersides during humid weather',
                'Premature defoliation starting from lower branches',
                'Fruit lesions causing cracking, distortion, and unmarketable appearance',
                'Reduced photosynthetic capacity leading to weakened trees',
                'Gall formation on juniper hosts (alternate host)',
                'Orange gelatinous horns emerging from cedar galls in spring'
            ],
            'remedies': [
                'Apply Myclobutanil 10% WP @ 0.5ml/L water at green tip stage',
                'Spray Tebuconazole 25.9% EC @ 1ml/L water every 14 days',
                'Use Triadimefon 25% WP @ 0.5g/L water from pre-bloom through summer',
                'Apply protective fungicides from green tip to petal fall stage',
                'Remove alternate host plants (juniper trees) within 2-mile radius if feasible',
                'Use systemic fungicides during critical infection periods',
                'Apply Propiconazole @ 1ml/L water for curative treatment',
                'Implement copper-based sprays during dormant season'
            ],
            'prevention': [
                'Plant cedar rust-resistant apple varieties (Liberty, Enterprise, Pristine)',
                'Remove or chemically treat nearby juniper and cedar trees',
                'Apply preventive fungicide sprays starting at green tip stage',
                'Monitor weather conditions closely for infection periods (wet, warm spring days)',
                'Ensure proper tree spacing for optimal air circulation',
                'Conduct regular orchard inspections during growing season',
                'Implement windbreaks to reduce spore dispersal',
                'Time pruning to avoid creating susceptible new growth during spore release'
            ],
            'organic_remedies': [
                'Sulfur spray @ 3g/L water during dry conditions (avoid hot weather)',
                'Copper soap fungicide application at recommended label rates',
                'Horticultural oil + sulfur combination for dual action',
                'Remove infected plant parts immediately and destroy',
                'Beneficial microorganism applications (Bacillus subtilis)',
                'Compost tea enriched with beneficial fungi',
                'Garlic and hot pepper spray as natural fungicide',
                'Encourage beneficial insects that feed on rust spores'
            ],
            'maintenance': [
                'Scout for symptoms weekly from bud break through summer',
                'Maintain detailed records of weather conditions and disease pressure',
                'Coordinate with neighboring property owners for area-wide management',
                'Regular soil testing and appropriate fertilization programs',
                'Proper irrigation management to avoid prolonged leaf wetness',
                'Annual evaluation of resistant variety performance'
            ]
        },
        
        'Apple_Scab': {
            'type': 'Fungal Disease',
            'pathogen': 'Venturia inaequalis',
            'severity': 'Very High',
            'economic_impact': 'Can cause 50-100% crop loss in susceptible varieties under favorable conditions',
            'description': 'Apple scab is the most economically important and widespread fungal disease of apples worldwide, causing significant losses in both yield and fruit quality.',
            'symptoms': [
                'Dark olive-green to black spots on leaves, typically starting on undersides',
                'Scabby, corky, and raised lesions on fruit surface',
                'Premature yellowing and drop of infected leaves',
                'Cracked and severely deformed fruit skin',
                'Reduced fruit size and complete unmarketability',
                'Secondary infections entering through scab-induced cracks',
                'Velvety appearance of lesions under humid conditions',
                'Complete defoliation in severe infection cases'
            ],
            'remedies': [
                'Apply Dodine 65% WP @ 1g/L water during early season (pre-bloom)',
                'Spray Captan 50% WP @ 2g/L water regularly throughout season',
                'Use Mancozeb 75% WP @ 2.5g/L water for protective coverage',
                'Apply elemental sulfur @ 3g/L water (avoid during hot weather)',
                'Rotate fungicide modes of action to prevent resistance development',
                'Time applications based on weather-driven infection models',
                'Use Flutriafol @ 0.3ml/L water for systemic protection',
                'Apply Kresoxim-methyl @ 0.5ml/L water for curative action'
            ],
            'prevention': [
                'Plant scab-resistant apple varieties (Liberty, Enterprise, Freedom, Prima)',
                'Remove and compost all fallen leaves in autumn (reduces inoculum)',
                'Prune trees for excellent air circulation and rapid leaf drying',
                'Apply dormant oil sprays in late winter to suppress overwintering spores',
                'Start protective fungicide program at green tip growth stage',
                'Monitor ascospore release using weather-based prediction models',
                'Maintain proper tree nutrition to promote natural disease resistance',
                'Implement sanitation practices including equipment disinfection'
            ],
            'organic_remedies': [
                'Lime sulfur spray during dormant season @ 3% concentration',
                'Baking soda @ 5g/L water + horticultural oil combination',
                'Weekly compost tea applications enriched with beneficial microbes',
                'Milk spray @ 1:10 ratio with water (lactoferrin antifungal properties)',
                'Potassium bicarbonate @ 5g/L water for alkaline fungicidal action',
                'Sodium bicarbonate @ 3g/L water + spreader-sticker',
                'Fermented plant extract sprays (nettle, horsetail)',
                'Clay-based foliar sprays for physical barrier protection'
            ],
            'maintenance': [
                'Daily weather monitoring during critical infection periods',
                'Regular calibration of spray equipment for proper coverage',
                'Detailed record keeping of all treatments and weather conditions',
                'Annual assessment of fungicide resistance development',
                'Coordination with extension services for regional disease alerts',
                'Proper storage and handling of fungicides according to label requirements'
            ]
        },
        
        'Apple_Healthy': {
            'type': 'Healthy Plant',
            'severity': 'N/A (Healthy)',
            'economic_impact': 'Positive - healthy trees produce maximum marketable fruit',
            'description': 'Apple fruit appears completely healthy with vibrant coloration, no disease symptoms, and excellent commercial quality potential.',
            'symptoms': [
                'Bright, uniform fruit coloration appropriate for variety',
                'Smooth, unblemished skin without spots or lesions',
                'Normal fruit size and shape for the cultivar',
                'Healthy green foliage with no discoloration',
                'Strong fruit attachment to branches',
                'No signs of decay, cracking, or deformation',
                'Fresh, crisp texture when tested',
                'Pleasant varietal aroma without off-odors'
            ],
            'maintenance': [
                'Continue regular deep watering schedule (1-2 inches per week)',
                'Apply balanced fertilizer (10-10-10 or 12-12-12) monthly during growing season',
                'Monitor weekly for early disease symptoms throughout season',
                'Maintain proper pruning schedule for optimal tree structure and health',
                'Keep orchard floor clean from fallen fruit and debris',
                'Inspect regularly for pest damage (aphids, mites, scale)',
                'Ensure proper harvest timing for maximum quality and storage life',
                'Conduct soil tests annually and amend as needed'
            ],
            'prevention': [
                'Maintain regular weekly health inspections throughout growing season',
                'Implement proper nutrition management based on annual soil testing',
                'Provide adequate water supply without creating waterlogged conditions',
                'Continue preventive spray schedule for common diseases and pests',
                'Practice comprehensive integrated pest management (IPM) program',
                'Ensure optimal harvest timing and gentle handling procedures',
                'Maintain proper post-harvest storage conditions',
                'Plan for regular equipment maintenance and calibration'
            ],
            'best_practices': [
                'Conduct annual comprehensive soil testing and amendment programs',
                'Apply appropriate organic mulch around tree base (maintain 6-inch clear zone)',
                'Implement regular equipment sanitization protocols',
                'Monitor weather patterns for potential disease pressure periods',
                'Maintain detailed orchard records for long-term management planning',
                'Participate in regional pest and disease monitoring programs',
                'Consider beneficial insect habitat enhancement',
                'Plan for sustainable long-term orchard productivity'
            ],
            'organic_remedies': [
                'Continue beneficial microorganism soil applications',
                'Apply compost tea monthly for soil and plant health',
                'Use organic mulches to maintain soil moisture and suppress weeds',
                'Implement companion planting for natural pest management',
                'Apply seaweed extract foliar feeds for trace element nutrition',
                'Use beneficial insect attractant plants around orchard perimeter'
            ],
            'remedies': [
                'No treatment required - maintain current excellent management practices',
                'Continue preventive care program that has achieved this healthy status',
                'Monitor closely to catch any potential issues before they become problems',
                'Maintain optimal growing conditions through proper cultural practices'
            ]
        },
        
        # Handle generic fruit classifications that your current model might return
        'APPLE': {
            'type': '🍎 Apple Fruit Detected',
            'severity': 'Model Classification Issue',
            'economic_impact': 'Requires proper disease-specific identification',
            'description': 'The system correctly identified this as an apple fruit, but could not determine the specific disease status. This suggests the model needs retraining for disease-specific classification.',
            'symptoms': [
                '✅ Apple fruit successfully detected with high confidence',
                '⚠️ However, specific disease classification was not determined',
                '🔍 The image shows an apple but disease status is unclear',
                '📊 Model confidence indicates good fruit identification',
                '🎯 Need disease-specific classification for proper diagnosis',
                '⚡ Consider using a specialized apple disease detection model'
            ],
            'remedies': [
                '🔄 Re-upload image with clearer disease symptoms if present',
                '💡 Try uploading images that clearly show disease lesions or healthy tissue',
                '📸 Use high-quality, well-lit images focused on fruit surface',
                '🔍 For disease identification, upload close-up images of affected areas',
                '👨‍🌾 Consult agricultural extension services for visual disease identification',
                '🧪 Consider laboratory testing for precise pathogen identification',
                '📚 Compare with visual disease identification guides',
                '🔄 If fruit appears healthy, it may be classified as "Healthy Apple"'
            ],
            'prevention': [
                '✅ Good news: Apple fruit properly identified by AI system',
                '🎯 For better results, use images showing clear disease symptoms',
                '📱 Ensure proper image quality: good lighting, focus, and resolution',
                '🔍 Focus camera on specific areas of interest (lesions, healthy tissue)',
                '⚖️ Consider multiple images from different angles if uncertain',
                '📖 Review common apple disease symptoms before photographing'
            ],
            'organic_remedies': [
                '🌿 General apple health: Regular organic care and monitoring',
                '🍃 Preventive organic sprays during growing season',
                '🧪 Natural fungicides for general disease prevention',
                '💧 Proper watering and nutrition management',
                '🌱 Beneficial microorganism applications',
                '🐛 Integrated pest management practices'
            ],
            'maintenance': [
                'Since this is an apple, follow general apple care guidelines',
                'Monitor for specific disease symptoms for accurate identification', 
                'Use disease-specific identification resources',
                'Consider professional agricultural consultation if problems persist'
            ]
        },
        
        # Handle other possible fruit classifications
        'MANGO': {
            'type': '🥭 Non-Apple Fruit Detected',
            'severity': 'Model Scope Limitation',
            'economic_impact': 'System optimized for apple diseases only',
            'description': 'The system detected a mango fruit, but this model is specifically designed for Apple disease identification only.',
            'symptoms': [
                '✅ Mango fruit successfully detected with high confidence',
                '⚠️ However, this system is trained only for Apple diseases',
                '🍎 Supported: Apple Black Rot, Apple Cedar Rust, Apple Scab, Apple Healthy',
                '❌ Not supported: Mango and other non-apple fruits',
                '🎯 For mango diseases, use specialized mango pathology resources',
                '🔄 For leaf diseases of other crops, try the Leaf Detection model'
            ],
            'remedies': [
                '🍎 For Apple diseases: Upload images of apple fruits with clear disease symptoms',
                '🍃 For other crop diseases: Switch to the Leaf Detection model',
                '🥭 For Mango-specific diseases: Consult mango pathology specialists',
                '📱 For general fruit diseases: Seek specialized agricultural apps',
                '👨‍🌾 Professional Help: Contact local agricultural experts',
                '📚 Research: Look up mango-specific disease identification guides'
            ],
            'prevention': [
                '✅ Use the correct model: Fruit Model = Apple diseases only',
                '🍃 Leaf Model = Multi-crop support (Tomato, Potato, Pepper)',
                '📸 For best results, use images matching the model training data',
                '🎯 Upload apple fruit images for fruit disease detection'
            ],
            'organic_remedies': [
                '🌿 General fruit care: Proper watering, nutrition, and pruning',
                '🛡️ Preventive measures: Regular monitoring and integrated pest management',
                '🌱 Organic protection: Neem oil, copper-based fungicides',
                '📚 Mango-specific: Research organic mango disease management'
            ],
            'maintenance': [
                'For accurate disease identification, use the appropriate model',
                'Apple fruits → Use Fruit Detection Model',
                'Other crop leaves → Use Leaf Detection Model',
                'Consult specialized resources for non-supported crops'
            ]
        }
    }
    
    # Comprehensive leaf disease database
    leaf_diseases = {
        'Pepper__bell___Bacterial_spot': {
            'type': 'Bacterial Disease',
            'pathogen': 'Xanthomonas campestris pv. vesicatoria',
            'severity': 'Medium to High',
            'economic_impact': 'Reduces fruit quality and marketability by 15-30%',
            'description': 'Bacterial spot causes lesions on pepper leaves, stems, and fruits, significantly impacting crop quality.',
            'symptoms': [
                'Small dark brown to black lesions on leaves',
                'Water-soaked margins around infected areas',
                'Fruit scarring and surface blemishes reducing market value',
                'Reduced overall marketable yield',
                'Premature leaf drop in severe infections',
                'Stem cankers in advanced disease cases',
                'Yellow halos around some leaf lesions',
                'Fruit cracking and secondary rot infections'
            ],
            'remedies': [
                'Apply copper-based bactericides @ 2-3g/L water weekly',
                'Use Streptomycin sulfate where legally permitted @ 200ppm',
                'Remove and destroy infected plant debris immediately',
                'Improve air circulation around plants through proper spacing',
                'Apply protective bactericide sprays preventively',
                'Use copper hydroxide @ 2g/L water for bacterial control',
                'Implement drip irrigation to reduce leaf wetness',
                'Apply Bacillus subtilis biological control agents'
            ],
            'prevention': [
                'Use certified disease-free seeds and transplants exclusively',
                'Practice strict 3-year crop rotation with non-host plants',
                'Avoid overhead irrigation systems that promote disease spread',
                'Maintain proper plant spacing (45-60cm apart) for air circulation',
                'Disinfect all tools between plants with 10% bleach solution',
                'Remove crop residues immediately after final harvest',
                'Implement plastic mulch to reduce soil splash',
                'Monitor and control insect vectors that spread bacteria'
            ],
            'organic_remedies': [
                'Copper soap applications according to organic certification standards',
                'Beneficial bacteria sprays (Pseudomonas fluorescens)',
                'Plant-based extracts (garlic, ginger) @ recommended concentrations',
                'Proper cultural practices emphasizing plant health',
                'Compost tea applications weekly for beneficial microorganisms',
                'Essential oil sprays (oregano, thyme) for natural antimicrobial action',
                'Baking soda solution @ 5g/L water for alkaline bactericidal effect'
            ],
            'maintenance': [
                'Weekly scouting for early symptom detection',
                'Weather monitoring for bacterial infection-favorable conditions',
                'Regular soil testing and appropriate fertilization',
                'Equipment calibration for proper spray coverage',
                'Record keeping of all treatments and their effectiveness'
            ]
        },
        
        'Pepper__bell___healthy': {
            'type': 'Healthy Plant',
            'severity': 'N/A (Healthy)',
            'economic_impact': 'Positive - healthy plants produce maximum marketable yield',
            'description': 'Bell pepper plant appears healthy with no signs of disease.',
            'symptoms': [
                'Vibrant green foliage with uniform coloration',
                'Strong, upright plant structure',
                'Normal leaf size and shape for variety',
                'No visible lesions, spots, or discoloration',
                'Healthy fruit development and attachment',
                'Good overall plant vigor and growth rate'
            ],
            'maintenance': [
                'Provide consistent watering (1 inch per week)',
                'Support plants as fruits develop using stakes or cages',
                'Monitor for common pepper diseases weekly',
                'Apply balanced fertilizer every 3-4 weeks during growing season',
                'Maintain proper plant spacing for good air flow',
                'Remove any fallen debris or diseased plant material'
            ],
            'prevention': [
                'Continue current healthy growing practices',
                'Regular monitoring for early disease symptoms',
                'Proper nutrition and consistent watering schedule',
                'Good garden hygiene and sanitation',
                'Preventive organic sprays if disease pressure increases'
            ],
            'organic_remedies': [
                'Continue beneficial soil microorganism applications',
                'Weekly compost tea for plant health maintenance',
                'Organic mulching to maintain soil moisture',
                'Companion planting for natural pest deterrence'
            ],
            'remedies': [
                'No treatment required - maintain excellent current practices',
                'Continue preventive care that achieved this healthy status',
                'Monitor closely for any changes in plant health'
            ]
        },
        
        'Tomato_Bacterial_spot': {
            'type': 'Bacterial Disease',
            'pathogen': 'Xanthomonas vesicatoria',
            'severity': 'High',
            'economic_impact': 'Can reduce yield by 30-50%',
            'description': 'Bacterial spot causes small, dark lesions on tomato leaves, stems, and fruits.',
            'symptoms': [
                'Small dark brown to black spots on leaves',
                'Water-soaked margins around lesions',
                'Yellow halos around spots on leaves',
                'Defoliation starting from lower leaves',
                'Fruit lesions with raised, corky texture',
                'Reduced photosynthetic area',
                'Stem lesions and cankers',
                'Secondary fruit rot infections'
            ],
            'remedies': [
                'Apply Copper-based bactericides @ 2-3g/L water',
                'Use Streptomycin sulfate 200-300 ppm spray',
                'Remove and destroy infected plant debris',
                'Apply Bacillus subtilis-based bio-fungicide',
                'Spray Bordeaux mixture (1%) during cool weather',
                'Improve drainage around plants',
                'Use copper hydroxide @ 2g/L water',
                'Apply protective bactericides preventively'
            ],
            'prevention': [
                'Use certified disease-free seeds and transplants',
                'Maintain proper plant spacing (45-60cm apart)',
                'Avoid overhead irrigation, use drip irrigation',
                'Remove crop residues immediately after harvest',
                'Practice 3-year crop rotation with non-solanaceous crops',
                'Disinfect tools with 10% bleach solution between plants',
                'Implement plastic mulch to reduce soil splash',
                'Control insect vectors of bacterial diseases'
            ],
            'organic_remedies': [
                'Neem oil spray @ 5ml/L water weekly',
                'Baking soda solution @ 5g/L water',
                'Garlic extract spray @ 50g/L water',
                'Copper soap fungicide application',
                'Beneficial bacteria applications',
                'Compost tea weekly applications',
                'Essential oil sprays for antimicrobial action'
            ]
        },
        
        'Tomato_Early_blight': {
            'type': 'Fungal Disease',
            'pathogen': 'Alternaria solani',
            'severity': 'High',
            'economic_impact': 'Yield losses of 25-75% possible',
            'description': 'Early blight is characterized by concentric ring lesions and affects leaves, stems, and fruits.',
            'symptoms': [
                'Circular to oval brown lesions with concentric rings',
                'Target-like appearance of lesions',
                'Yellow halos around lesions',
                'Lower leaves affected first, progressing upward',
                'Stem lesions near soil line',
                'Fruit lesions at stem end with dark, sunken areas',
                'Premature defoliation',
                'Reduced plant vigor and yield'
            ],
            'remedies': [
                'Apply Mancozeb 75% WP @ 2.5g/L water',
                'Spray Chlorothalonil 75% WP @ 2g/L water',
                'Use Azoxystrobin 23% SC @ 1ml/L water',
                'Apply Propiconazole 25% EC @ 1ml/L water',
                'Alternate fungicide sprays every 10-14 days',
                'Remove lower leaves touching ground',
                'Improve air circulation around plants',
                'Apply protective fungicides preventively'
            ],
            'prevention': [
                'Use resistant varieties like Mountain Fresh Plus',
                'Ensure excellent air circulation between plants',
                'Water at soil level, avoid wetting foliage',
                'Apply balanced fertilizer, avoid excess nitrogen',
                'Mulch around plants to reduce soil splash',
                'Practice crop rotation with non-host crops',
                'Remove crop debris after harvest',
                'Start plants from disease-free seeds or transplants'
            ],
            'organic_remedies': [
                'Weekly compost tea applications',
                'Milk spray @ 1:10 ratio with water',
                'Trichoderma viride soil application',
                'Potassium bicarbonate spray @ 5g/L water',
                'Calcium chloride foliar spray',
                'Neem oil applications',
                'Copper-based organic fungicides'
            ]
        },
        
        'Tomato_Late_blight': {
            'type': 'Oomycete Disease',
            'pathogen': 'Phytophthora infestans',
            'severity': 'Very High',
            'economic_impact': 'Can cause 100% crop loss in favorable conditions',
            'description': 'Late blight is a devastating disease that can destroy entire tomato crops rapidly.',
            'symptoms': [
                'Water-soaked lesions on leaves',
                'White fuzzy growth on leaf undersides in humid conditions',
                'Brown to black lesions spreading rapidly',
                'Affected fruits show brown, greasy lesions',
                'Complete plant collapse in severe cases',
                'Distinctive musty odor from infected plants',
                'Dark stem lesions and blackening',
                'Rapid disease progression under favorable conditions'
            ],
            'remedies': [
                'Apply Metalaxyl + Mancozeb @ 2.5g/L water',
                'Spray Dimethomorph 50% WP @ 1.5g/L water',
                'Use Copper oxychloride 50% WP @ 3g/L water',
                'Apply Fosetyl aluminum @ 2.5g/L water',
                'Emergency spraying during disease outbreak',
                'Remove infected plants immediately',
                'Improve air circulation and drainage',
                'Apply protective fungicides preventively'
            ],
            'prevention': [
                'Plant resistant varieties like Mountain Magic',
                'Ensure excellent air circulation',
                'Never use overhead watering',
                'Remove infected plants immediately and destroy',
                'Apply preventive copper sprays in humid conditions',
                'Monitor weather for blight-favorable conditions',
                'Use certified disease-free plants',
                'Implement proper sanitation practices'
            ],
            'organic_remedies': [
                'Bordeaux mixture application @ 1% concentration',
                'Copper soap spray during preventive periods',
                'Remove and burn infected plant parts immediately',
                'Improve drainage around plants',
                'Beneficial microorganism soil amendments',
                'Milk spray for early prevention',
                'Baking soda solutions'
            ]
        },
        
        'Tomato_Leaf_Mold': {
            'type': 'Fungal Disease',
            'pathogen': 'Passalora fulva',
            'severity': 'Medium',
            'economic_impact': 'Yield reduction of 10-25%',
            'description': 'Leaf mold primarily affects greenhouse tomatoes causing yellowing and defoliation.',
            'symptoms': [
                'Yellow patches on upper leaf surfaces',
                'Olive-green to brown fuzzy growth on undersides',
                'Progressive yellowing and browning of leaves',
                'Lower leaves affected first',
                'Defoliation in severe cases',
                'Reduced fruit quality and yield',
                'Velvet-like fungal growth on leaf undersides',
                'Premature aging of affected plants'
            ],
            'remedies': [
                'Improve ventilation and reduce humidity',
                'Apply Chlorothalonil @ 2g/L water',
                'Use Mancozeb @ 2.5g/L water',
                'Remove affected leaves immediately',
                'Increase spacing between plants',
                'Apply copper-based fungicides',
                'Improve air circulation in growing areas',
                'Reduce leaf wetness duration'
            ],
            'prevention': [
                'Maintain humidity below 85%',
                'Ensure good air circulation',
                'Use resistant varieties',
                'Avoid overhead watering',
                'Remove crop debris promptly',
                'Proper greenhouse ventilation',
                'Monitor and control humidity levels',
                'Adequate plant spacing'
            ],
            'organic_remedies': [
                'Sulfur spray @ 3g/L water',
                'Baking soda solution @ 5g/L water',
                'Milk spray @ 1:10 ratio',
                'Compost tea applications',
                'Beneficial microorganism sprays',
                'Copper soap fungicides',
                'Essential oil treatments'
            ]
        },
        
        'Potato___Early_blight': {
            'type': 'Fungal Disease',
            'pathogen': 'Alternaria solani',
            'severity': 'Medium',
            'economic_impact': 'Yield reductions of 15-30% common',
            'description': 'Early blight affects potato foliage and tubers, causing significant yield reductions.',
            'symptoms': [
                'Circular brown lesions with concentric rings',
                'Target-like patterns on leaves',
                'Yellow halos around lesions',
                'Premature defoliation',
                'Dark, sunken lesions on tubers',
                'Reduced photosynthetic capacity',
                'Lower leaves affected first',
                'Progressive upward movement of disease'
            ],
            'remedies': [
                'Apply Mancozeb 75% WP @ 2.5g/L water',
                'Use Chlorothalonil @ 2g/L water',
                'Spray Azoxystrobin @ 1ml/L water',
                'Apply protective fungicides preventively',
                'Remove affected foliage',
                'Ensure proper field drainage',
                'Rotate fungicide modes of action',
                'Time applications based on weather conditions'
            ],
            'prevention': [
                'Plant certified disease-free seed potatoes',
                'Practice 3-4 year crop rotation',
                'Avoid overhead irrigation systems',
                'Maintain proper plant nutrition',
                'Remove volunteer potato plants',
                'Hill soil around plants properly',
                'Implement proper field sanitation',
                'Monitor weather for infection periods'
            ],
            'organic_remedies': [
                'Copper-based organic fungicides',
                'Compost tea applications',
                'Beneficial microorganism inoculants',
                'Proper crop residue management',
                'Neem oil treatments',
                'Baking soda sprays',
                'Milk applications'
            ]
        },
        
        'Potato___Late_blight': {
            'type': 'Oomycete Disease',
            'pathogen': 'Phytophthora infestans',
            'severity': 'Very High',
            'economic_impact': 'Can destroy entire crops within days',
            'description': 'Late blight is historically significant, causing the Irish Potato Famine.',
            'symptoms': [
                'Water-soaked lesions on leaves',
                'White mold growth on undersides',
                'Rapid blackening and death of foliage',
                'Brown, dry lesions on tubers',
                'Foul odor from secondary bacterial infection',
                'Complete field destruction possible',
                'Dark, greasy lesions spreading rapidly',
                'Plant collapse under favorable conditions'
            ],
            'remedies': [
                'Apply Metalaxyl-M + Mancozeb @ 2.5g/L',
                'Use Dimethomorph @ 1.5g/L water',
                'Spray copper-based fungicides',
                'Emergency applications during outbreaks',
                'Destroy infected plants immediately',
                'Avoid harvesting infected tubers',
                'Improve field drainage',
                'Apply protective fungicides preventively'
            ],
            'prevention': [
                'Use certified seed potatoes',
                'Plant resistant varieties',
                'Monitor weather conditions closely',
                'Avoid overhead irrigation',
                'Practice proper field sanitation',
                'Time planting to avoid favorable conditions',
                'Implement area-wide management',
                'Remove volunteer plants'
            ],
            'organic_remedies': [
                'Copper sulfate applications',
                'Bordeaux mixture spray',
                'Immediate removal of infected plants',
                'Improve air circulation',
                'Beneficial microorganism applications',
                'Proper cultural practices',
                'Enhanced drainage'
            ]
        },
        
        'Potato___healthy': {
            'type': 'Healthy Plant',
            'severity': 'N/A (Healthy)',
            'economic_impact': 'Positive - healthy plants produce maximum yield',
            'description': 'Potato plant shows healthy growth with no disease symptoms.',
            'symptoms': [
                'Vigorous green foliage with normal coloration',
                'Strong, upright plant structure',
                'Normal leaf size and shape',
                'No visible lesions or discoloration',
                'Healthy root and tuber development',
                'Good plant vigor throughout growing season'
            ],
            'maintenance': [
                'Maintain consistent soil moisture',
                'Hill soil around plants as they grow',
                'Monitor for pest and disease symptoms',
                'Apply appropriate fertilizers based on soil test',
                'Ensure proper field sanitation',
                'Continue good cultural practices'
            ],
            'prevention': [
                'Continue current excellent management',
                'Regular monitoring for early symptoms',
                'Maintain proper nutrition program',
                'Good field hygiene practices',
                'Preventive disease management'
            ]
        },
        
        'Tomato_healthy': {
            'type': 'Healthy Plant',
            'severity': 'N/A (Healthy)',
            'economic_impact': 'Positive - healthy plants produce maximum yield',
            'description': 'Tomato plant appears healthy with vibrant green foliage and no disease symptoms.',
            'symptoms': [
                'Vibrant green leaves with uniform coloration',
                'Strong, sturdy plant structure',
                'Normal leaf size and shape for variety',
                'No visible lesions, spots, or discoloration',
                'Healthy fruit development and ripening',
                'Good overall plant vigor and growth'
            ],
            'maintenance': [
                'Continue regular watering schedule (1-2 inches per week)',
                'Apply balanced fertilizer every 2-3 weeks',
                'Monitor for early disease symptoms',
                'Maintain proper staking and pruning',
                'Keep garden area clean from debris',
                'Continue current excellent practices'
            ],
            'prevention': [
                'Continue healthy growing practices',
                'Regular monitoring for early symptoms',
                'Proper nutrition and watering',
                'Good garden hygiene',
                'Preventive organic sprays if needed'
            ]
        }
    }
    
    # Return disease information based on classification
    if model_type == 'fruit':
        return fruit_diseases.get(disease_class, {
            'type': 'Unknown Classification',
            'severity': 'Requires Investigation',
            'description': f'The classification "{disease_class}" is not recognized in the disease database.',
            'symptoms': [
                f'AI classified this as "{disease_class}" with {confidence:.1%} confidence',
                'This classification is not in the trained apple disease categories',
                'Expected: Apple Black Rot, Apple Cedar Rust, Apple Scab, Apple Healthy, or generic Apple/Mango detection'
            ],
            'remedies': [
                'Verify the fruit_classes.json mapping file contains correct disease names',
                'Check that the model was trained for disease classification, not general fruit classification',
                'Upload a clearer image showing disease symptoms or healthy tissue',
                'Consult agricultural experts for proper disease identification'
            ],
            'prevention': [
                'Use proper disease classification models trained on apple diseases',
                'Ensure mapping files match the model training classes',
                'Upload high-quality images with clear disease symptoms'
            ]
        })
    
    elif model_type == 'leaf':
        return leaf_diseases.get(disease_class, {
            'type': 'Unknown Disease',
            'severity': 'Unknown',
            'description': 'Disease information not available in the leaf disease database.',
            'symptoms': ['Consult agricultural expert for proper identification'],
            'remedies': ['Seek professional agricultural consultation'],
            'prevention': ['Follow general crop protection practices']
        })
    
    # Default fallback
    return {
        'type': 'Unknown Disease',
        'severity': 'Unknown',
        'description': 'Disease information not available in database.',
        'symptoms': ['Consult agricultural expert for proper identification'],
        'remedies': ['Seek professional agricultural consultation'],
        'prevention': ['Follow general crop protection practices']
    }

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(img_path):
    """Preprocess image for model prediction"""
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        img_array = image.img_to_array(img)
        img_array = img_array / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        return img_array
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        raise

def save_prediction_to_db(model_type, predicted_class, confidence, class_index, filename, user_ip):
    """Save prediction to database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO predictions (model_type, predicted_class, confidence, class_index, filename, user_ip)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (model_type, predicted_class, confidence, class_index, filename, user_ip))
        prediction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return prediction_id
    except Exception as e:
        logger.error(f"Error saving prediction: {e}")
        return None

@app.route('/')
def index():
    return jsonify({
        "message": "CropGuard AI - Multi-Crop Disease Detection API v3.0",
        "models_loaded": {k: v is not None for k, v in models.items()},
        "total_classes": {k: len(v) for k, v in class_mappings.items()},
        "supported_diseases": {
            "fruit_model": ["Apple Black Rot", "Apple Cedar Rust", "Apple Scab", "Apple Healthy"],
            "leaf_model": ["Tomato, Potato, Bell Pepper diseases"]
        },
        "version": "3.0",
        "contact": {
            "email": CONTACT_EMAIL,
            "whatsapp": WHATSAPP_NUMBER
        }
    })

@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    if 'model_type' not in request.form:
        return jsonify({'error': 'Model type not specified (fruit/leaf)'}), 400
    
    model_type = request.form['model_type']
    
    if model_type not in models or models[model_type] is None:
        return jsonify({'error': f'{model_type} model not available'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        file.save(filepath)
        
        processed_image = preprocess_image(filepath)
        predictions = models[model_type].predict(processed_image, verbose=0)
        predicted_class_index = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class_index])
        
        predicted_class = class_mappings[model_type].get(
            predicted_class_index, 
            f"Unknown_Class_{predicted_class_index}"
        )
        
        disease_info = get_comprehensive_disease_info(predicted_class, model_type, confidence)
        
        user_ip = request.remote_addr or 'unknown'
        prediction_id = save_prediction_to_db(
            model_type, predicted_class, confidence, 
            predicted_class_index, unique_filename, user_ip
        )
        
        result = {
            'prediction_id': prediction_id,
            'model_type': model_type,
            'predicted_class': predicted_class,
            'confidence': confidence,
            'class_index': int(predicted_class_index),
            'timestamp': datetime.now().isoformat(),
            'disease_info': disease_info
        }
        
        logger.info(f"{model_type} prediction: {predicted_class} with confidence {confidence:.4f}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500
    
    finally:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.get_json()
        required_fields = ['prediction_id', 'rating', 'is_correct']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        prediction_id = data['prediction_id']
        rating = data['rating']
        is_correct = data['is_correct']
        comment = data.get('comment', '')
        
        if not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM predictions WHERE id = ?', (prediction_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Prediction not found'}), 404
        
        cursor.execute('''
            INSERT INTO feedback (prediction_id, rating, is_correct, comment)
            VALUES (?, ?, ?, ?)
        ''', (prediction_id, rating, is_correct, comment))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Feedback submitted successfully'})
        
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        return jsonify({'error': 'Failed to save feedback'}), 500

@app.route('/history', methods=['GET'])
def get_prediction_history():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        model_filter = request.args.get('model_type', '')
        
        # Check what columns exist in the predictions table
        cursor.execute("PRAGMA table_info(predictions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Build query based on available columns
        select_fields = ['p.id', 'p.timestamp', 'p.predicted_class', 'p.confidence']
        if 'model_type' in columns:
            select_fields.append('p.model_type')
        
        select_clause = ', '.join(select_fields)
        
        query = f'''
            SELECT {select_clause}, 
                   f.rating, f.is_correct, f.comment
            FROM predictions p
            LEFT JOIN feedback f ON p.id = f.prediction_id
        '''
        params = []
        
        if model_filter and 'model_type' in columns:
            query += ' WHERE p.model_type = ?'
            params.append(model_filter)
        
        query += ' ORDER BY p.timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            entry = {
                'id': row[0],
                'timestamp': row[1],
                'predicted_class': row[2],
                'confidence': row[3]
            }
            
            idx = 4
            if 'model_type' in columns:
                entry['model_type'] = row[idx] or 'leaf'
                idx += 1
            else:
                entry['model_type'] = 'leaf'
            
            # Add feedback data
            entry['rating'] = row[idx]
            entry['is_correct'] = row[idx + 1]
            entry['comment'] = row[idx + 2]
            
            history.append(entry)
        
        conn.close()
        return jsonify(history)
        
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'error': 'Failed to retrieve history'}), 500

@app.route('/analytics', methods=['GET'])
def get_analytics():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(confidence) FROM predictions')
        avg_confidence = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(DISTINCT user_ip) FROM predictions')
        total_users = cursor.fetchone()[0]
        
        conn.close()
        
        analytics_data = {
            'total_predictions': total_predictions,
            'total_users': total_users,
            'average_confidence': round(avg_confidence, 4),
            'system_accuracy': {
                'fruit_model': 99.77,
                'leaf_model': 95.50
            }
        }
        
        return jsonify(analytics_data)
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': 'Failed to retrieve analytics'}), 500

@app.route('/contact', methods=['POST'])
def submit_contact():
    try:
        data = request.get_json()
        required_fields = ['name', 'email', 'message']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields: name, email, message'}), 400
        
        name = data['name']
        email = data['email']
        subject = data.get('subject', 'CropGuard AI Contact Form Submission')
        message = data['message']
        
        # Save to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO contacts (name, email, subject, message)
            VALUES (?, ?, ?, ?)
        ''', (name, email, subject, message))
        conn.commit()
        conn.close()
        
        # Send email notification
        try:
            msg = Message(
                subject=f"CropGuard AI Contact: {subject}",
                recipients=[CONTACT_EMAIL],
                body=f"New contact: {name} ({email}): {message}"
            )
            mail.send(msg)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
        
        # Generate WhatsApp URL
        whatsapp_message = f"New Contact: {name} ({email}): {message[:100]}..."
        whatsapp_url = f"https://api.whatsapp.com/send?phone={WHATSAPP_NUMBER.replace('+', '')}&text={whatsapp_message}"
        
        return jsonify({
            'message': 'Contact form submitted successfully!',
            'whatsapp_notification': whatsapp_url
        })
        
    except Exception as e:
        logger.error(f"Error processing contact form: {e}")
        return jsonify({'error': 'Failed to submit contact form'}), 500

@app.route('/stats', methods=['GET'])
def get_system_stats():
    """Get overall system statistics"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM predictions')
        total_predictions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT user_ip) FROM predictions')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM contacts')
        total_contacts = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_predictions': total_predictions,
            'total_users': total_users,
            'total_contacts': total_contacts,
            'version': '3.0',
            'contact_email': CONTACT_EMAIL,
            'contact_whatsapp': WHATSAPP_NUMBER
        })
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return jsonify({'error': 'Failed to retrieve stats'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'models_loaded': {k: v is not None for k, v in models.items()},
        'timestamp': datetime.now().isoformat(),
        'version': '3.0'
    })

if __name__ == '__main__':
    load_models()
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)