import schedule
import time
from datetime import datetime
from utils.internet_checker import InternetDiseaseChecker
from utils.dynamic_trainer import DynamicModelTrainer
from utils.disease_database import DiseaseDatabase
import sqlite3

class HealthSystemScheduler:
    def __init__(self):
        self.internet_checker = InternetDiseaseChecker()
        self.trainer = DynamicModelTrainer()
        self.db = DiseaseDatabase()

    def daily_internet_check(self):
        """Daily check for new diseases from internet"""
        print(f"\n[{datetime.now()}] Starting daily internet disease check...")
        try:
            new_diseases = self.internet_checker.perform_internet_check()
            if new_diseases:
                print(f"Found {len(new_diseases)} new diseases, retraining model...")
                self.trainer.train_model()
            else:
                print("No new diseases found")
        except Exception as e:
            print(f"Daily check failed: {e}")

    def weekly_model_retrain(self):
        """Weekly full model retrain"""
        print(f"\n[{datetime.now()}] Starting weekly model retrain...")
        try:
            success = self.trainer.train_model(force_retrain=True)
            if success:
                stats = self.trainer.get_model_stats()
                print(f"Model retrained successfully. Stats: {stats}")
            else:
                print("Model retrain failed")
        except Exception as e:
            print(f"Weekly retrain failed: {e}")

    def monthly_database_cleanup(self):
        """Monthly cleanup of old/unreliable data"""
        print(f"\n[{datetime.now()}] Starting monthly database cleanup...")
        try:
            # Remove diseases with very low confidence that haven't been updated recently
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM diseases
                    WHERE confidence < 0.05
                      AND updated_at < datetime('now', '-90 days')
                      AND source = 'internet'
                    """
                )
                deleted_count = cursor.rowcount
                conn.commit()

            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} low-confidence diseases")
                # Retrain after cleanup
                self.trainer.train_model()
            else:
                print("No cleanup needed")

        except Exception as e:
            print(f"Database cleanup failed: {e}")

    def health_system_health_check(self):
        """Check overall system health"""
        print(f"\n[{datetime.now()}] System health check...")

        try:
            # Check database
            diseases = self.db.get_all_diseases()
            print(f"Database: {len(diseases)} diseases")

            # Check model
            stats = self.trainer.get_model_stats()
            if stats:
                print(f"Model: {stats['n_classes']} classes, {stats['n_features']} features")
            else:
                print("Model: Not available")

            # Check internet connectivity
            import requests
            try:
                requests.get("https://www.google.com", timeout=5)
                print("Internet: Connected")
            except:
                print("Internet: Disconnected")

        except Exception as e:
            print(f"Health check failed: {e}")

    def start_scheduler(self):
        """Start the automated scheduler"""
        print("Starting Health System Scheduler...")

        # Schedule tasks
        schedule.every().day.at("02:00").do(self.daily_internet_check)  # 2 AM daily
        schedule.every().week.do(self.weekly_model_retrain)  # Weekly
        schedule.every(30).days.do(self.monthly_database_cleanup)  # Monthly
        schedule.every().hour.do(self.health_system_health_check)  # Hourly health check

        # Run initial checks
        self.health_system_health_check()
        self.daily_internet_check()

        print("Scheduler started. Press Ctrl+C to stop.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped by user")

    def manual_update(self):
        """Manual trigger for updates"""
        print("Running manual system update...")
        self.daily_internet_check()
        self.weekly_model_retrain()
        self.health_system_health_check()
        print("Manual update complete")

# Global scheduler instance
scheduler = HealthSystemScheduler()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "manual":
        scheduler.manual_update()
    else:
        scheduler.start_scheduler()
