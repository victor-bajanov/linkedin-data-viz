import pandas as pd
import os
from typing import Dict, Optional
import warnings
warnings.filterwarnings('ignore')


class LinkedInDataLoader:
    """Load and process LinkedIn data export CSV files"""

    def __init__(self, data_directory: str):
        self.data_directory = data_directory
        self.data: Dict[str, Optional[pd.DataFrame]] = {}

    def load_csv_safely(self, filepath: str, name: str) -> Optional[pd.DataFrame]:
        """Safely load a CSV file with error handling"""
        try:
            if os.path.exists(filepath):
                # Try different encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        df = pd.read_csv(filepath, encoding=encoding)
                        print(f"✓ Loaded {name}: {len(df)} rows")
                        return df
                    except UnicodeDecodeError:
                        continue
                    except pd.errors.EmptyDataError:
                        print(f"⚠ Empty file: {name}")
                        return pd.DataFrame()
                    except Exception as e:
                        print(f"✗ Error loading {name}: {str(e)}")
                        return None
            else:
                print(f"✗ File not found: {filepath}")
                return None
        except Exception as e:
            print(f"✗ Error loading {name}: {str(e)}")
            return None

    def load_all_data(self) -> Dict[str, Optional[pd.DataFrame]]:
        """Load all LinkedIn CSV files"""

        # Update base directory to point to data folder
        data_dir = os.path.join(self.data_directory, 'data')

        # Define file mappings
        file_mappings = {
            # Profile and personal data
            'profile': 'Profile.csv',
            'profile_summary': 'Profile Summary.csv',
            'registration': 'Registration.csv',
            'email_addresses': 'Email Addresses.csv',
            'phone_numbers': 'PhoneNumbers.csv',
            'whatsapp_numbers': 'Whatsapp Phone Numbers.csv',

            # Professional information
            'positions': 'Positions.csv',
            'education': 'Education.csv',
            'certifications': 'Certifications.csv',
            'skills': 'Skills.csv',
            'languages': 'Languages.csv',
            'honors': 'Honors.csv',
            'organizations': 'Organizations.csv',

            # Network and social
            # 'connections': 'Connections.csv',  # Special handling needed
            'invitations': 'Invitations.csv',
            'company_follows': 'Company Follows.csv',
            'events': 'Events.csv',

            # Endorsements and recommendations
            'endorsement_received': 'Endorsement_Received_Info.csv',
            'endorsement_given': 'Endorsement_Given_Info.csv',
            'recommendations_received': 'Recommendations_Received.csv',
            'recommendations_given': 'Recommendations_Given.csv',

            # Messages and communication
            'messages': 'messages.csv',
            'coach_messages': 'coach_messages.csv',
            'guide_messages': 'guide_messages.csv',
            'learning_coach_messages': 'learning_coach_messages.csv',
            'learning_role_play_messages': 'learning_role_play_messages.csv',

            # Job search
            'job_applications': 'Jobs/Job Applications.csv',
            'job_seeker_preferences': 'Jobs/Job Seeker Preferences.csv',
            'saved_jobs': 'Jobs/Saved Jobs.csv',
            'saved_job_alerts': 'SavedJobAlerts.csv',
            'job_screening_questions': 'Job Applicant Saved Screening Question Responses.csv',

            # Learning
            'learning': 'Learning.csv',

            # Financial
            'receipts': 'Receipts.csv',
            'receipts_v2': 'Receipts_v2.csv',

            # Other
            'ad_targeting': 'Ad_Targeting.csv',
            'rich_media': 'Rich_Media.csv',
            'private_identity': 'Private_identity_asset.csv',
            'verifications': 'Verifications/Verifications.csv'
        }

        # Load each file
        for key, filename in file_mappings.items():
            filepath = os.path.join(data_dir, filename)
            self.data[key] = self.load_csv_safely(filepath, key)

        # Special handling for Connections.csv
        try:
            connections_path = os.path.join(data_dir, 'Connections.csv')
            if os.path.exists(connections_path):
                # Skip the header notes (first 3 lines)
                self.data['connections'] = pd.read_csv(connections_path, skiprows=3, encoding='utf-8')
                print(f"✓ Loaded connections: {len(self.data['connections'])} rows")
        except Exception as e:
            print(f"✗ Error loading connections: {str(e)}")
            self.data['connections'] = None


        # Clean up common date columns
        self._process_dates()

        # Add derived fields
        self._add_derived_fields()

        return self.data

    def _process_dates(self):
        """Process and standardize date columns across all dataframes"""
        date_mappings = {
            'connections': ['Connected On'],
            'positions': ['Started On', 'Finished On'],
            # 'education': ['Start Date', 'End Date'],  # Don't convert - these are just years
            'endorsement_received': ['Endorsement Date'],
            'messages': ['DATE'],
            'job_applications': ['Application Date'],
            'learning': ['Content Last Watched Date (if viewed)', 'Content Completed At (if completed)'],
            'receipts_v2': ['Transaction Made At'],
            'company_follows': ['Followed On'],
            'events': ['Start Time', 'End Time']
        }

        for df_name, date_columns in date_mappings.items():
            df = self.data.get(df_name)
            if df is not None and not df.empty:
                for col in date_columns:
                    if col in df.columns:
                        try:
                            # Try parsing with different formats
                            if df_name == 'connections' and col == 'Connected On':
                                # Format: "16 Sep 2025"
                                df[col] = pd.to_datetime(df[col], format='%d %b %Y', errors='coerce')
                            elif df_name == 'positions':
                                # Don't use UTC for positions to avoid timezone conflicts
                                df[col] = pd.to_datetime(df[col], errors='coerce')
                            else:
                                df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
                        except:
                            pass

    def _add_derived_fields(self):
        """Add useful derived fields to the dataframes"""

        # Add duration to positions
        positions = self.data.get('positions')
        if positions is not None and not positions.empty:
            if 'Started On' in positions.columns and 'Finished On' in positions.columns:
                positions['Started On'] = pd.to_datetime(positions['Started On'], errors='coerce')
                positions['Finished On'] = pd.to_datetime(positions['Finished On'], errors='coerce')

                # Calculate duration in months
                try:
                    current_time = pd.Timestamp.now()
                    finished_dates = positions['Finished On'].fillna(current_time)
                    positions['Duration_Months'] = (
                        (finished_dates - positions['Started On'])
                        .dt.total_seconds() / (30 * 24 * 3600)
                    ).round().astype('Int64')
                except:
                    positions['Duration_Months'] = None

                # Mark current positions
                positions['Is_Current'] = positions['Finished On'].isna()

        # Add year to education
        education = self.data.get('education')
        if education is not None and not education.empty:
            if 'Start Date' in education.columns:
                education['Start Year'] = pd.to_datetime(education['Start Date'], errors='coerce').dt.year
            if 'End Date' in education.columns:
                education['End Year'] = pd.to_datetime(education['End Date'], errors='coerce').dt.year

        # Extract company from connections
        connections = self.data.get('connections')
        if connections is not None and not connections.empty:
            # Try to ensure we have the right column names
            if 'Connected On' not in connections.columns:
                # Try to find the date column
                for col in connections.columns:
                    if 'date' in col.lower() or 'connected' in col.lower():
                        connections.rename(columns={col: 'Connected On'}, inplace=True)
                        break

    def get_summary_stats(self) -> dict:
        """Get summary statistics about the loaded data"""
        stats = {}
        for name, df in self.data.items():
            if df is not None:
                stats[name] = {
                    'rows': len(df),
                    'columns': len(df.columns),
                    'memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024
                }
        return stats


if __name__ == "__main__":
    # Test the data loader
    loader = LinkedInDataLoader('/workspace/linkedin')
    data = loader.load_all_data()

    print("\n=== Data Summary ===")
    stats = loader.get_summary_stats()
    for name, stat in stats.items():
        if stat['rows'] > 0:
            print(f"{name}: {stat['rows']} rows, {stat['columns']} columns")

    print("\n=== Sample Data ===")
    # Show sample of key dataframes
    key_dataframes = ['profile', 'connections', 'positions', 'skills']
    for key in key_dataframes:
        df = data.get(key)
        if df is not None and not df.empty:
            print(f"\n{key.upper()}:")
            print(df.head(2))
            print(f"Columns: {', '.join(df.columns[:5])}")