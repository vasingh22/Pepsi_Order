import type { Invoice } from '../types/invoice';

export const mockInvoices: Invoice[] = [
  {
    id: '2025-HYD-004216',
    invoice_number: '2025-HYD-004216',
    invoice_date: '2025-10-28',
    status: 'Approved',
    statusMessage: '',
    store_name: 'Big Bazaar',
    address: '45 MG Road, Bangalore - 560001',
    gst_number: '29AABCU9603R1ZV',
    buyer_details: {
      name: 'PepsiCo India Holdings Pvt Ltd',
      address: 'Plot 18, Sector 15, Hyderabad - 500002',
      contact: '+91-9876543210'
    },
    seller_details: {
      name: 'Big Bazaar',
      address: '45 MG Road, Bangalore - 560001',
      gst_number: '29AABCU9603R1ZV'
    },
    items: [
      {
        name: 'Pepsi 2L',
        hsn_code: '22021010',
        quantity: 50,
        unit: 'bottle',
        rate: 80.00,
        discount: 0,
        amount: 4000.00
      },
      {
        name: 'Mountain Dew 1L',
        hsn_code: '22021020',
        quantity: 30,
        unit: 'bottle',
        rate: 50.00,
        discount: 0,
        amount: 1500.00
      },
      {
        name: 'Lays Classic 100g',
        hsn_code: '19059030',
        quantity: 100,
        unit: 'packet',
        rate: 25.00,
        discount: 0,
        amount: 2500.00
      }
    ],
    charges: {
      subtotal: 8000.00
    },
    tax_details: {
      type: 'GST',
      rate: 12,
      amount: 960.00
    },
    round_off: 0.00,
    total: 8960.00,
    payment_details: {
      mode: 'Credit',
      paid: false,
      due_date: '2025-11-15'
    }
  },
  {
    id: '2025-HYD-004217',
    invoice_number: '2025-HYD-004217',
    invoice_date: '2025-10-27',
    status: 'Flagged',
    statusMessage: 'Missing SKU price',
    store_name: 'Reliance Fresh',
    address: '78 Park Street, Kolkata - 700016',
    gst_number: '19AABCU9603R1ZV',
    buyer_details: {
      name: 'PepsiCo India Holdings Pvt Ltd',
      address: 'Plot 18, Sector 15, Hyderabad - 500002',
      contact: '+91-9876543210'
    },
    seller_details: {
      name: 'Reliance Fresh',
      address: '78 Park Street, Kolkata - 700016',
      gst_number: '19AABCU9603R1ZV'
    },
    items: [
      {
        name: 'Pepsi 500ml',
        hsn_code: '22021010',
        quantity: 200,
        unit: 'bottle',
        rate: 20.00,
        discount: 0,
        amount: 4000.00
      },
      {
        name: 'Kurkure Masala 90g',
        quantity: 150,
        unit: 'packet',
        rate: 0,
        discount: 0,
        amount: 0
      }
    ],
    charges: {
      subtotal: 4000.00
    },
    tax_details: {
      type: 'GST',
      rate: 12,
      amount: 480.00
    },
    round_off: 0.00,
    total: 4480.00,
    payment_details: {
      mode: 'Cash',
      paid: true
    }
  },
  {
    id: '2025-HYD-004218',
    invoice_number: '2025-HYD-004218',
    invoice_date: '2025-10-28',
    status: 'Pending',
    statusMessage: 'Low OCR confidence on total value',
    store_name: 'Sai Super Mart',
    address: '123 Market Road, Hyderabad - 500001',
    gst_number: '36ABCDE1234F1ZV',
    buyer_details: {
      name: 'PepsiCo India Holdings Pvt Ltd',
      address: 'Plot 18, Sector 15, Hyderabad - 500002',
      contact: '+91-9876543210'
    },
    seller_details: {
      name: 'Sai Super Mart',
      address: '123 Market Road, Hyderabad - 500001',
      gst_number: '36ABCDE1234F1ZV'
    },
    items: [
      {
        name: 'Pepsi 1L',
        hsn_code: '22021010',
        quantity: 36,
        unit: 'bottle',
        rate: 45.00,
        discount: 0,
        amount: 1620.00
      },
      {
        name: 'Mountain Dew 600ml',
        hsn_code: '22021020',
        quantity: 24,
        unit: 'bottle',
        rate: 35.00,
        discount: 0,
        amount: 840.00
      },
      {
        name: 'Lays 50g',
        hsn_code: '19059030',
        quantity: 48,
        unit: 'packet',
        rate: 20.00,
        discount: 0,
        amount: 960.00
      }
    ],
    charges: {
      subtotal: 3420.00
    },
    tax_details: {
      type: 'GST',
      rate: 5,
      amount: 171.00
    },
    round_off: 0.00,
    total: 3591.00,
    payment_details: {
      mode: 'Cash',
      paid: false,
      due_date: '2025-11-05'
    }
  },
  {
    id: '2025-HYD-004219',
    invoice_number: '2025-HYD-004219',
    invoice_date: '2025-10-26',
    status: 'In Review',
    statusMessage: 'Partial total mismatch',
    store_name: 'More Megastore',
    address: '234 Gandhi Nagar, Chennai - 600020',
    gst_number: '33AABCU9603R1ZV',
    buyer_details: {
      name: 'PepsiCo India Holdings Pvt Ltd',
      address: 'Plot 18, Sector 15, Hyderabad - 500002',
      contact: '+91-9876543210'
    },
    seller_details: {
      name: 'More Megastore',
      address: '234 Gandhi Nagar, Chennai - 600020',
      gst_number: '33AABCU9603R1ZV'
    },
    items: [
      {
        name: 'Tropicana Orange 1L',
        hsn_code: '20091100',
        quantity: 40,
        unit: 'bottle',
        rate: 95.00,
        discount: 0,
        amount: 3800.00
      },
      {
        name: 'Quaker Oats 1kg',
        hsn_code: '19041000',
        quantity: 25,
        unit: 'packet',
        rate: 180.00,
        discount: 0,
        amount: 4500.00
      }
    ],
    charges: {
      subtotal: 8300.00
    },
    tax_details: {
      type: 'GST',
      rate: 12,
      amount: 996.00
    },
    round_off: 4.00,
    total: 9300.00,
    payment_details: {
      mode: 'UPI',
      paid: true
    }
  },
  {
    id: '2025-HYD-004220',
    invoice_number: '2025-HYD-004220',
    invoice_date: '2025-10-25',
    status: 'Flagged',
    statusMessage: 'Unreadable date',
    store_name: 'D-Mart',
    address: '567 Link Road, Mumbai - 400050',
    gst_number: '27AABCU9603R1ZV',
    buyer_details: {
      name: 'PepsiCo India Holdings Pvt Ltd',
      address: 'Plot 18, Sector 15, Hyderabad - 500002',
      contact: '+91-9876543210'
    },
    seller_details: {
      name: 'D-Mart',
      address: '567 Link Road, Mumbai - 400050',
      gst_number: '27AABCU9603R1ZV'
    },
    items: [
      {
        name: '7UP 2L',
        hsn_code: '22021010',
        quantity: 60,
        unit: 'bottle',
        rate: 75.00,
        discount: 0,
        amount: 4500.00
      },
      {
        name: 'Lays Spanish Tomato 125g',
        hsn_code: '19059030',
        quantity: 80,
        unit: 'packet',
        rate: 30.00,
        discount: 0,
        amount: 2400.00
      }
    ],
    charges: {
      subtotal: 6900.00
    },
    tax_details: {
      type: 'GST',
      rate: 12,
      amount: 828.00
    },
    round_off: -2.00,
    total: 7726.00,
    payment_details: {
      mode: 'Card',
      paid: false,
      due_date: '2025-11-10'
    }
  }
];

