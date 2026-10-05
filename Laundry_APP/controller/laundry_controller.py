from model.laundry_model import LaundryService, LaundryItem

class LaundryController:
    """Controller class to manage interactions between model and view"""
    def __init__(self):
        self.service = LaundryService()
        self.view = None
        
    def set_view(self, view):
        """Set the view component"""
        self.view = view
        
    def start_new_order(self, phone):
        """Start a new order with the given phone number"""
        # Save the phone number for future use
        self.service.save_last_phone_number(phone)
        
        # Create a new order
        return self.service.create_order(phone)
    
    def add_item_to_order(self, name, quantity, service_type, rate):
        """Add an item to the current order"""
        if not self.service.current_order:
            return False
            
        item = LaundryItem(name, quantity, service_type, rate)
        self.service.current_order.add_item(item)
        return True
    
    def remove_item_from_order(self, index):
        """Remove an item from the current order"""
        if not self.service.current_order:
            return False
            
        self.service.current_order.remove_item(index)
        return True
    
    def get_service_types(self):
        """Get available service types"""
        return self.service.service_types
    
    def get_item_name_types(self):
        """Get available item name types"""
        return self.service.item_name
    
    def get_customer_orders(self, phone):
        """Get order history for a customer"""
        return self.service.get_customer_orders(phone)
    
    def process_receipt(self, receipt_type='pdf'):
        """Process the receipt (PDF or SMS)"""
        if not self.service.current_order:
            return False, "No active order"
            
        if receipt_type == 'pdf':
            return self.service.generate_pdf_receipt(self.service.current_order)
        elif receipt_type == 'sms':
            return self.service.send_sms_receipt()
        else:
            return False, "Invalid receipt type"
    
    def get_last_phone_number(self):
        """Get the last used phone number"""
        return self.service.get_last_phone_number()
        
    def auto_continue(self, phone):
        """Handle auto-continue for returning customers"""
        return self.start_new_order(phone)
        
    def cleanup(self):
        """Clean up resources"""
        if self.service:
            self.service.close_connection()
            
        # Save order to database first
        self.service.save_order_to_db(self.service.current_order)
        
        if receipt_type.lower() == 'pdf':
            return self.service.generate_pdf_receipt(self.service.current_order)
        elif receipt_type.lower() == 'sms':
            return self.service.send_sms(self.service.current_order)
        else:
            return False, f"Unknown receipt type: {receipt_type}"
    
    def get_last_phone_number(self):
        """Get the last used phone number"""
        return self.service.last_phone_number
    
    def auto_continue(self, phone):
        """Auto-continue with a returning customer"""
        try:
            # Create a new order for the customer
            order = self.start_new_order(phone)
            if not order:
                return False, "Failed to create order"
                
            # Get customer's order history
            orders = self.get_customer_orders(phone)
            if not orders or len(orders) == 0:
                return False, "No previous orders found"
                
            return True, "Order created successfully"
        except Exception as e:
            return False, f"Error in auto_continue: {str(e)}"
    
    def cleanup(self):
        """Clean up resources"""
        self.service.cleanup()
