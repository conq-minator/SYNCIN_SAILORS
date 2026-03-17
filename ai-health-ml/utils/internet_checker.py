import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import re
from utils.disease_database import DiseaseDatabase

class InternetDiseaseChecker:
    def __init__(self):
        self.db = DiseaseDatabase()
        self.last_check = None
        self.check_interval = timedelta(hours=24)  # Check once per day

    def should_check_internet(self):
        """Check if we should perform internet search"""
        if self.last_check is None:
            return True
        return datetime.now() - self.last_check > self.check_interval

    def search_new_diseases_ollama(self, symptoms_query):
        """Use Ollama to research potential new diseases"""
        try:
            # This would use Ollama if available
            # For now, we'll simulate with web search
            return self.search_web_for_diseases(symptoms_query)
        except Exception as e:
            print(f"Ollama search failed: {e}")
            return []

    def search_web_for_diseases(self, symptoms_query):
        """Search web for diseases related to symptoms"""
        try:
            # Use a medical search API or web scraping
            # For demo, we'll use PubMed or similar
            query = f"diseases associated with {symptoms_query}"
            url = f"https://pubmed.ncbi.nlm.nih.gov/?term={query.replace(' ', '+')}"

            # Note: In real implementation, you'd use official APIs
            # This is a simplified version
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=12)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract potential disease names from search results
            # This is simplified - real implementation would parse properly
            potential_diseases = []

            # Common disease indicators
            disease_keywords = [
                'syndrome', 'disease', 'disorder', 'condition', 'infection',
                'virus', 'bacterial', 'fungal', 'parasitic', 'autoimmune'
            ]

            # Prefer PubMed result titles (more reliable than raw text regex)
            titles = soup.select("a.docsum-title")
            for a in titles[:12]:
                t = " ".join(a.get_text(" ", strip=True).split())
                if t:
                    # Pull short disease-like phrases from the title
                    # (keep it simple; this is only for suggestion seeding)
                    if any(k in t.lower() for k in disease_keywords):
                        potential_diseases.append(t)

            # Fallback: extract a few title-cased phrases from page text
            if not potential_diseases:
                words = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b", soup.get_text())
                for w in words[:60]:
                    wl = w.lower()
                    if any(k in wl for k in disease_keywords) and w not in ['Disease', 'Syndrome', 'Disorder']:
                        potential_diseases.append(w)
                        if len(potential_diseases) >= 8:
                            break

            # Clean + dedup + cap
            cleaned = []
            for p in potential_diseases:
                name = re.sub(r"\s+", " ", str(p)).strip()
                # Avoid extremely long titles
                if len(name) > 80:
                    name = name[:77] + "..."
                if name and name.lower() not in {c.lower() for c in cleaned}:
                    cleaned.append(name)
                if len(cleaned) >= 5:
                    break

            return cleaned  # top 5 unique-ish

        except Exception as e:
            print(f"Web search failed: {e}")
            return []

    def check_health_news(self):
        """Check for new health news and emerging diseases"""
        try:
            # Check WHO, CDC, or health news sites
            sources = [
                'https://www.who.int/news-room',
                'https://www.cdc.gov/media/index.html'
            ]

            new_diseases = []

            for url in sources:
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Look for headlines mentioning new diseases
                    headlines = soup.find_all(['h1', 'h2', 'h3', 'h4'])

                    for headline in headlines[:10]:
                        text = headline.get_text().strip()
                        if any(keyword in text.lower() for keyword in
                              ['new disease', 'emerging', 'outbreak', 'pandemic', 'epidemic']):
                            # Extract potential disease name
                            disease_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
                            if disease_match:
                                new_diseases.append(disease_match.group(1))

                except Exception as e:
                    print(f"Failed to check {url}: {e}")
                    continue

            return list(set(new_diseases))

        except Exception as e:
            print(f"Health news check failed: {e}")
            return []

    def add_new_disease_from_internet(self, disease_name, symptoms, source='internet'):
        """Add a new disease discovered from internet research"""
        try:
            # Check if disease already exists
            existing = self.db.get_all_diseases()
            existing_names = [d['name'].lower() for d in existing]

            if disease_name.lower() not in existing_names:
                # Add to database
                disease_id = self.db.add_disease(
                    name=disease_name,
                    symptoms=symptoms,
                    description=f"Discovered from {source} on {datetime.now().strftime('%Y-%m-%d')}",
                    source=source,
                    confidence=0.1  # Low confidence for new discoveries
                )

                print(f"Added new disease: {disease_name} (ID: {disease_id})")
                return True
            else:
                print(f"Disease {disease_name} already exists")
                return False

        except Exception as e:
            print(f"Failed to add disease {disease_name}: {e}")
            return False

    def perform_internet_check(self):
        """Main function to check internet for new diseases"""
        if not self.should_check_internet():
            print("Internet check not needed yet")
            return []

        print("Performing internet disease check...")

        new_diseases_found = []

        # Check health news for emerging diseases
        emerging_diseases = self.check_health_news()
        for disease in emerging_diseases:
            if self.add_new_disease_from_internet(disease, [], 'health_news'):
                new_diseases_found.append(disease)

        # Check for diseases related to common symptoms
        common_symptoms = ['fever', 'cough', 'fatigue', 'headache']
        for symptom in common_symptoms:
            potential_diseases = self.search_web_for_diseases(symptom)
            for disease in potential_diseases:
                if self.add_new_disease_from_internet(disease, [symptom], 'web_search'):
                    new_diseases_found.append(disease)

        self.last_check = datetime.now()

        if new_diseases_found:
            print(f"Found {len(new_diseases_found)} new diseases: {', '.join(new_diseases_found)}")
        else:
            print("No new diseases found")

        return new_diseases_found

    def get_disease_trends(self):
        """Get trending diseases from recent additions"""
        recent = self.db.get_recent_diseases(days=30)
        return [dict(zip(['id', 'name', 'description', 'symptoms', 'source', 'confidence', 'created_at', 'updated_at'], row))
                for row in recent]

# Initialize checker
if __name__ == "__main__":
    checker = InternetDiseaseChecker()
    new_diseases = checker.perform_internet_check()
    print(f"Internet check complete. New diseases: {new_diseases}")
