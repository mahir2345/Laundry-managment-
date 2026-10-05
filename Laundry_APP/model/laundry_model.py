import re
import os
import sqlite3
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Optional: Twilio integration (comment out if not needed)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    print("Twilio not installed. SMS functionality will be disabled.")


class LaundryItem:
    """Model for a single laundry item"""
    def __init__(self, name, quantity, service_type, rate):
        self.name = name
        self.quantity = quantity
        self.service_type = service_type
        self.rate = rate
        self.subtotal = quantity * rate

    def to_dict(self):
        return {
            'name': self.name,
            'quantity': self.quantity,
            'service_type': self.service_type,
            'rate': self.rate,
            'subtotal': self.subtotal
        }


class LaundryOrder:
    """Model for the complete laundry order"""
    def __init__(self, customer_phone):
        self.customer_phone = customer_phone
        self.items = []
        self.order_id = self._generate_order_id()
        self.created_at = datetime.now()
        
    def _generate_order_id(self):
        """Generate unique order ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        phone_suffix = self.customer_phone[-4:]
        return f"ORD{timestamp}{phone_suffix}"
    
    def add_item(self, item):
        """Add item to order"""
        self.items.append(item)
    
    def remove_item(self, index):
        """Remove item from order"""
        if 0 <= index < len(self.items):
            self.items.pop(index)
    
    def get_total(self):
        """Calculate total amount"""
        return sum(item.subtotal for item in self.items)
    
    def validate_phone(self):
        """Validate phone number format"""
        pattern = r'(\+?\d{10,13})'
        return re.fullmatch(pattern, self.customer_phone) is not None


class LaundryService:
    """Service layer for business logic"""
    def __init__(self):
        self.current_order = None
        self.service_types = ['Wash & Fold', 'Dry Clean', 'Iron Only', 'Wash & Iron', 'Premium Clean']
        self.item_name = ['Shirt', 'Pants', 'T-Shirt','Polo','Sweater','Jacket','Suits','Sari','Other']
        self.last_phone_number = None

        # Initialize database connection
        self.conn = None
        self.cursor = None
        self.init_db()
        
        # Load last used phone number
        self.load_last_phone_number()

        # Twilio configuration (replace with your actual credentials)
        self.twilio_configured = False
        if TWILIO_AVAILABLE:
            self.account_sid = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
            self.auth_token = 'your_auth_token_here'
            self.twilio_number = '+1234567890'
            # Check if credentials are configured
            if not self.account_sid.startswith('ACxx'):
                self.twilio_configured = True
                
    def init_db(self):
        """Initialize the database"""
        try:
            # Close any existing connection first
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self.conn = None
                self.cursor = None
            
            # Use a timeout to handle locked database
            self.db_path = 'laundry_data.db'
            self.conn = sqlite3.connect(self.db_path, timeout=10)
            self.cursor = self.conn.cursor()
            
            # Check if tables exist before creating them
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
            table_exists = self.cursor.fetchone()
            
            if not table_exists:
                # Create orders table
                self.cursor.execute('''
                    CREATE TABLE orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT UNIQUE,
                        customer_phone TEXT,
                        created_at TEXT,
                        total_amount REAL
                    )
                ''')
                
                # Create order items table
                self.cursor.execute('''
                    CREATE TABLE order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id TEXT,
                        item_name TEXT,
                        quantity INTEGER,
                        service_type TEXT,
                        rate REAL,
                        subtotal REAL,
                        FOREIGN KEY (order_id) REFERENCES orders (order_id)
                    )
                ''')
                
                self.conn.commit()
                print("Database created successfully")
            else:
                print("Using existing database")
        except Exception as e:
            print(f"Database initialization error: {e}")
            self.conn = None
            self.cursor = None
            
    def clean_old_orders(self):
        """Clean up orders older than 30 days"""
        try:
            # Ensure database connection is active
            if not self.conn or not self.cursor:
                self.init_db()
                
            # Calculate date 30 days ago
            import datetime
            thirty_days_ago = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Get order IDs to delete
            self.cursor.execute('''
                SELECT order_id FROM orders 
                WHERE created_at < ?
            ''', (thirty_days_ago,))
            
            old_order_ids = [row[0] for row in self.cursor.fetchall()]
            
            # Delete old order items first (due to foreign key constraint)
            for order_id in old_order_ids:
                self.cursor.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
            
            # Delete old orders
            self.cursor.execute('DELETE FROM orders WHERE created_at < ?', (thirty_days_ago,))
            
            # Commit changes
            self.conn.commit()
            
            if old_order_ids:
                print(f"Cleaned up {len(old_order_ids)} orders older than 30 days")
                
        except Exception as e:
            print(f"Error cleaning old orders: {e}")
    
    def get_customer_orders(self, phone):
        """Get all orders for a customer"""
        try:
            # Ensure database connection is active
            if not self.conn or not self.cursor:
                self.init_db()
            
            # Clean up old orders first
            self.clean_old_orders()
                
            # Get basic order information
            self.cursor.execute('''
                SELECT order_id, created_at, total_amount 
                FROM orders 
                WHERE customer_phone = ? 
                ORDER BY created_at DESC
            ''', (phone,))
            
            orders = self.cursor.fetchall()
            
            # For each order, get the items
            result = []
            for order in orders:
                order_id, created_at, total_amount = order
                
                # Get items for this order
                self.cursor.execute('''
                    SELECT item_name, quantity, service_type, rate, subtotal
                    FROM order_items
                    WHERE order_id = ?
                ''', (order_id,))
                
                items = self.cursor.fetchall()
                
                # Add order with its items to result
                result.append({
                    'order_id': order_id,
                    'created_at': created_at,
                    'total_amount': total_amount,
                    'items': items
                })
                
            return result
        except Exception as e:
            print(f"Error fetching customer orders: {e}")
            return []
            
    def save_order_to_db(self, order):
        """Save order to database"""
        try:
            # Ensure database connection is active
            if not self.conn or not self.cursor:
                self.init_db()
            
            # Format created_at as string if it's a datetime object
            created_at = order.created_at
            if hasattr(order.created_at, 'strftime'):
                created_at = order.created_at.strftime('%Y-%m-%d %H:%M:%S')
                
            # Save order details
            self.cursor.execute('''
                INSERT OR REPLACE INTO orders (order_id, customer_phone, created_at, total_amount)
                VALUES (?, ?, ?, ?)
            ''', (order.order_id, order.customer_phone, created_at, order.get_total()))
            
            # Save order items
            for item in order.items:
                self.cursor.execute('''
                    INSERT INTO order_items (order_id, item_name, quantity, service_type, rate, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order.order_id, item.name, item.quantity, item.service_type, item.rate, item.subtotal))
            
            self.conn.commit()
            print(f"Order {order.order_id} saved to database successfully")
            return True
        except Exception as e:
            print(f"Error saving order to database: {e}")
            return False
            
    def save_last_phone_number(self, phone):
        """Save the last used phone number to the database"""
        try:
            # Ensure database connection is active
            if not self.conn or not self.cursor:
                self.init_db()
                
            # Check if settings table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
            table_exists = self.cursor.fetchone()
            
            if not table_exists:
                # Create settings table
                self.cursor.execute('''
                    CREATE TABLE settings (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                ''')
                
            # Save last phone number
            self.cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', ('last_phone_number', phone))
            
            self.conn.commit()
            self.last_phone_number = phone
            print(f"Saved last phone number: {phone}")
            return True
        except Exception as e:
            print(f"Error saving last phone number: {e}")
            return False
    
    def load_last_phone_number(self):
        """Load the last used phone number from the database"""
        # Disabled automatic loading of last phone number
        # to prevent showing a fixed number when the app starts
        return None
        
        # Original implementation (commented out)
        # try:
        #     # Ensure database connection is active
        #     if not self.conn or not self.cursor:
        #         self.init_db()
        #         
        #     # Check if settings table exists
        #     self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
        #     table_exists = self.cursor.fetchone()
        #     
        #     if not table_exists:
        #         return None
        #         
        #     # Load last phone number
        #     self.cursor.execute('''
        #         SELECT value FROM settings WHERE key = ?
        #     ''', ('last_phone_number',))
        #     
        #     result = self.cursor.fetchone()
        #     if result:
        #         self.last_phone_number = result[0]
        #         print(f"Loaded last phone number: {self.last_phone_number}")
        #         return self.last_phone_number
        #     return None
        # except Exception as e:
        #     print(f"Error loading last phone number: {e}")
        #     return None
    
    def cleanup(self):
        """Close database connection and perform cleanup"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
                print("Database connection closed successfully")
        except Exception as e:
            print(f"Error closing database connection: {e}")
    
    def create_order(self, phone):
        """Create new order"""
        self.current_order = LaundryOrder(phone)
        return self.current_order
    
    def generate_pdf_receipt(self, order):
        """Generate PDF receipt"""
        try:
            # Create directory if it doesn't exist
            if not os.path.exists('receipts'):
                os.makedirs('receipts')
                
            # Save to receipts directory with absolute path
            filename = f"receipts/receipt_{order.order_id}.pdf"
            abs_path = os.path.abspath(filename)
            
            c = canvas.Canvas(abs_path, pagesize=letter)
            width, height = letter
            
            # Header
            c.setFont("Helvetica-Bold", 20)
            c.drawString(200, height - 50, "LAUNDRY SERVICE RECEIPT")
            
            # Order details
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 100, f"Order ID: {order.order_id}")
            
            # Format date as string to avoid strftime issues
            date_str = order.created_at
            if hasattr(order.created_at, 'strftime'):
                date_str = order.created_at.strftime('%Y-%m-%d %H:%M')
                
            c.drawString(50, height - 120, f"Date: {date_str}")
            c.drawString(50, height - 140, f"Customer Phone: {order.customer_phone}")
            
            # Items header
            y = height - 180
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Item")
            c.drawString(200, y, "Service")
            c.drawString(350, y, "Qty")
            c.drawString(400, y, "Rate")
            c.drawString(450, y, "Subtotal")
            
            # Items list
            y -= 20
            c.setFont("Helvetica", 11)
            for item in order.items:
                c.drawString(50, y, item.name[:25])
                c.drawString(200, y, item.service_type[:20])
                c.drawString(350, y, str(item.quantity))
                c.drawString(400, y, f"{item.rate:.2f}")
                c.drawString(450, y, f"{item.subtotal:.2f}")
                y -= 20
            
            # Total
            y -= 20
            c.setFont("Helvetica-Bold", 14)
            c.drawString(350, y, "TOTAL:")
            c.drawString(450, y, f"TK {order.get_total():.2f}")
            
            # Footer - use standard font instead of Italic which might be missing
            c.setFont("Helvetica", 10)
            c.drawString(50, 50, "Thank you for choosing our laundry service!")
            
            c.save()
            return True, abs_path
        except Exception as e:
            print(f"PDF generation error: {e}")
            return False, str(e)
    
    def send_sms(self, order):
        """Send SMS notification"""
        if not TWILIO_AVAILABLE:
            return False, "Twilio library not installed. Please install it using 'pip install twilio'"
        
        if not self.twilio_configured:
            return False, "Twilio credentials not configured. Please update account_sid, auth_token, and twilio_number in the LaundryService class."
        
        # Validate phone number format for Twilio
        phone = order.customer_phone
        if not phone.startswith('+'):
            # Add + prefix if missing
            phone = '+' + phone
        
        try:
            client = Client(self.account_sid, self.auth_token)
            
            # Build message
            items_text = "\n".join([
                f"- {item.name} ({item.service_type}) x{item.quantity}"
                for item in order.items[:5]  # Limit to first 5 items for SMS
            ])
            
            if len(order.items) > 5:
                items_text += f"\n... and {len(order.items) - 5} more items"
            
            message_body = (
                f"Laundry Service Receipt\n"
                f"Order ID: {order.order_id}\n"
                f"Items:\n{items_text}\n"
                f"Total: TK {order.get_total():.2f}\n"
                f"We'll notify you when ready!"
            )
            
            message = client.messages.create(
                body=message_body,
                from_=self.twilio_number,
                to=phone
            )
            print(f"SMS sent successfully to {phone}")
            return True, "SMS sent successfully"
        except Exception as e:
            print(f"SMS sending error: {e}")
            return False, f"Failed to send SMS: {str(e)}"
            
        # For testing without Twilio
        # Uncomment the line below to simulate successful SMS sending during testing
        # return True, "SMS sent successfully (Test Mode)"
    
    def close_connection(self):
        """Close the database connection"""
        if hasattr(self, 'conn') and self.conn:
            try:
                self.conn.close()
                print("Database connection closed")
            except Exception as e:
                print(f"Error closing database connection: {e}")
