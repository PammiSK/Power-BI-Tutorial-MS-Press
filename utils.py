import re
import io
import pandas as pd

def markdown(report: str):
    print("Processing: Markdown Report")

    # Precompile regexes
    date_re  = re.compile(r"(\d{2}/\d{2}/\d{4} \d{1,2}:\d{2} [AP]M)")
    style_re = re.compile(r"^(?:[0-9]{6}E?|SPK)")
    soh_re   = re.compile(r"^\s{12}[A-Za-z]")

    def department_from_style(code):
        if code.startswith("1"):
            return "Womenswear"
        if code.startswith("2"):
            return "Menswear"
        if code.startswith("SPK"):
            return "Kidswear"
        if code[0] in ("5", "7"):
            return "Accessories"
        return "Others"
    
    rows = []
    flag = False
    current = {}

    for line in report.splitlines():
        line = line.rstrip("\n")
        if line.startswith("Markdown:"):
            parts = line.split()
            md_desc = parts[3]
            flag = not md_desc.startswith(("SB", "JG", "JAG"))
            if flag:
                current = {
                    "markdown_id": parts[1],
                    "markdown_description": md_desc
                }
        elif flag and line.startswith("Effective"):
            current["date"] = line.split()[2]
        elif flag and style_re.match(line):
            parts = [p.strip() for p in line.split("  ") if p.strip()]
            code = parts[0]
            current.update({
                "style_code": code,
                "description": parts[-1],
                "department": department_from_style(code)
            })
        elif flag and soh_re.match(line):
            parts = [p.strip() for p in line.split("  ") if p.strip()]
            colour, soh, price = parts[0], int(parts[1]), float(parts[-1])
            
            rows.append({
                **current,
                "colour": colour,
                "soh": soh,
                "price": price
            })
        elif date_re.match(line):
            ts = line.rsplit(" ", 1)[0]
            time_stamp = ts.replace("/", "-").replace(":", ".")

    # Build DataFrame once
    df = pd.DataFrame(rows)

    # Build price history dict per group
    hist = (
        df
        .groupby(["style_code", "description", "colour"])
        .apply(lambda g: {
            row.price: (row.date, row.markdown_description)
            for _, row in g.iterrows()
        })
        .reset_index(name="price_history")
    )

    # Select the lowest-price row in each group
    idx = df.groupby(["style_code", "description", "colour"])["price"].idxmin()
    min_rows = df.loc[idx]

    # Merge history and sort
    deduped = (
        min_rows
        .merge(hist, on=["style_code", "description", "colour"])
        .sort_values(["style_code", "colour"])
    )

    return deduped

def sales_perf_inc_gst_on_retail(report: str):
    print("Processing: Sales Performance (Incl. GST on Retail $)")
    
    df_attributes = [
        'sales_person',
        'retail_$_incl_disc',
        'discount',
        'returns',
        'net_$',
        'avg_sale_units',
        'avg_sale_$',
        '%_store_total'
    ]
    rows = []
    
    for l in report.splitlines():
        line = l.rstrip("\n")
        if not line.endswith("%"):
            continue

        # split into tokens
        data = line.split()

        # skip any "Total" row by checking the first field
        if data[0].startswith("Total"):
            continue

        # if name has spaces, rejoin all except last 7 tokens
        if len(data) != len(df_attributes):
            name = " ".join(data[:-7])
            rest = data[-7:]
            data = [name] + rest

        rows.append(data)

    df = pd.DataFrame(rows,columns=df_attributes)

    float_attrs = ['retail_$_incl_disc', 'discount', 'returns', 'net_$', 'avg_sale_units', 'avg_sale_$', '%_store_total']

    for col in float_attrs:
        s = df[col].astype(str).str.replace(',', '')
        if col == '%_store_total':
            s = s.str.rstrip('%')
        df[col] = s.astype(float)

    # ensure string columns are of type str
    df['sales_person'] = df['sales_person'].astype(str)
    
    return df

def sales_perf_exc_gst_on_retail(report: str):
    print("Processing: Sales Performance (Excl. GST on Retail $)")
    df_attributes = [
        'sales_person',
        'retail_$_incl_disc',
        'discount',
        'returns',
        'net_$',
        'avg_sale_units',
        'avg_sale_$',
        '%_store_total'
    ]
    rows = []

    for l in report.splitlines():
        line = l.rstrip("\n")
        if not line.endswith("%"):
            continue

        # split into tokens
        data = line.split()

        # skip any "Total" row by checking the first field
        if data[0].startswith("Total"):
            continue

        # if name has spaces, rejoin all except last 7 tokens
        if len(data) != len(df_attributes):
            name = " ".join(data[:-7])
            rest = data[-7:]
            data = [name] + rest

        rows.append(data)

    df = pd.DataFrame(rows,columns=df_attributes)

    float_attrs = ['retail_$_incl_disc', 'discount', 'returns', 'net_$', 'avg_sale_units', 'avg_sale_$', '%_store_total']

    for col in float_attrs:
        s = df[col].astype(str).str.replace(',', '')
        if col == '%_store_total':
            s = s.str.rstrip('%')
        df[col] = s.astype(float)

    # ensure string columns are of type str
    df['sales_person'] = df['sales_person'].astype(str)
    
    return df

def sales_perf_inc_tax_on_net(report: str):
    print("Processing: Sales Performance (Incl. Tax on Net $)")
    
    df_attributes = [
        'sales_person',
        'retail_$_after_disc',
        'discount',
        'returns',
        'net_$',
        '#_of_trans',
        'avg_sale_units',
        'avg_sale_$',
        '%_store_total'
    ]
    rows = []

    for l in report.splitlines():
        line = l.rstrip("\n")
        if not line.endswith("%"):
            continue

        # split into tokens
        data = line.split()

        # skip any "Total" row by checking the first field
        if data[0].startswith("Total"):
            continue        
        
        # if name has spaces, rejoin all except last 8 tokens
        
        name = " ".join(data[:-8])
        rest = data[-8:]
        data = [name] + rest

        rows.append(data)

    df = pd.DataFrame(rows,columns=df_attributes)

    float_attrs = ['retail_$_after_disc', 'discount', 'returns', 'net_$', 'avg_sale_units', 'avg_sale_$', '%_store_total']

    for col in float_attrs:
        s = df[col].astype(str).str.replace(',', '')
        if col == '%_store_total':
            s = s.str.rstrip('%')
        df[col] = s.astype(float)

    # ensure string columns are of type str
    df['sales_person'] = df['sales_person'].astype('string')

    # ensure string columns are of type int
    df['#_of_trans'] = df['#_of_trans'].astype(str).str.replace(',', '').astype(int)
    
    return df

def sales_perf_exc_tax_on_net(report: str):
    print("Processing: Sales Performance (Excl. Tax on Net $)")
    
    df_attributes = [
        'sales_person',
        'retail_$_after_disc',
        'discount',
        'returns',
        'net_$',
        '#_of_trans',
        'avg_sale_units',
        'avg_sale_$',
        '%_store_total'
    ]
    rows = []

    for l in report.splitlines():
        line = l.rstrip("\n")
        if not line.endswith("%"):
            continue

        # split into tokens
        data = line.split()

        # skip any "Total" row by checking the first field
        if data[0].startswith("Total"):
            continue        
        
        # if name has spaces, rejoin all except last 8 tokens
        
        name = " ".join(data[:-8])
        rest = data[-8:]
        data = [name] + rest

        rows.append(data)

    df = pd.DataFrame(rows,columns=df_attributes)

    float_attrs = ['retail_$_after_disc', 'discount', 'returns', 'net_$', 'avg_sale_units', 'avg_sale_$', '%_store_total']

    for col in float_attrs:
        s = df[col].astype(str).str.replace(',', '')
        if col == '%_store_total':
            s = s.str.rstrip('%')
        df[col] = s.astype(float)

    # ensure string columns are of type str
    df['sales_person'] = df['sales_person'].astype('string')

    # ensure string columns are of type int
    df['#_of_trans'] = df['#_of_trans'].astype(str).str.replace(',', '').astype(int)

def best_sellers_qty(report: str):
    print("Processing: Best Sellers by Quantity")
    
    price_re = re.compile(r"\.\d{2}\s*$")
    df_attributes = ['style', 'colour', 'qty', 'avg_price', 'net_$']
    rows = []

    for line in report.splitlines():
    # with open("06 BEST SELLERS REPORT BY VALUE.txt", encoding="utf-8") as f: # yields the same result        
        line = line.rstrip("\n")
        if price_re.search(line):
            data = line.split()
            
            if data[0].startswith("Total") or data[0].startswith("Gross"):
                continue
            
            if len(data) != len(df_attributes):
                name = " ".join(data[1:-3]).title()
                # print(data[-3:])
                data = [data[0]] + [name] + data[-3:]
            
            rows.append(data)

    df = pd.DataFrame(rows,columns=df_attributes)
                
    for col in df_attributes:
        if col == 'qty':
            df[col] = df[col].astype(int)
        elif col == 'net_$' or col == 'avg_price':
            s = df[col].astype(str).str.replace('$', '')
            df[col] = s.astype(float)
        elif col == 'style' or col == 'colour':
            df[col] = df[col].astype('string')
    
    return df

def best_sellers_value(report: str):
    print("Processing: Best Sellers by Value")
    price_re = re.compile(r"\.\d{2}\s*$")

    df_attributes = ['style', 'colour', 'qty', 'avg_price', 'net_$']
    rows = []
    
    for line in report.splitlines():
        line = line.rstrip("\n")
        if price_re.search(line):
            data = line.split()
            
            if data[0].startswith("Total") or data[0].startswith("Gross"):
                continue
            
            if len(data) != len(df_attributes):
                name = " ".join(data[1:-3]).title()
                # print(data[-3:])
                data = [data[0]] + [name] + data[-3:]
            
            rows.append(data)
        df = pd.DataFrame(rows,columns=df_attributes)
            
    for col in df_attributes:
        if col == 'qty':
            df[col] = df[col].astype(int)
        elif col == 'net_$' or col == 'avg_price':
            s = df[col].astype(str).str.replace('$', '')
            df[col] = s.astype(float)
        elif col == 'style' or col == 'colour':
            df[col] = df[col].astype('string')
    
    return df

def daily_sales_summary(report: str):
    print("Processing: Daily Sales Summary")
    price_re = re.compile(r"\.\d{2}\s*$")
    df_attributes = ['day', 'date', 'gross', 'disc', 'net', 'ex_gst']
    rows = []

    for line in report.splitlines():
        line = line.rstrip("\n")
        if price_re.search(line):
            data = line.split()
            rows.append(data)

    df = pd.DataFrame(rows,columns=df_attributes)

    float_cols = ['gross', 'disc', 'net', 'ex_gst']
    for col in float_cols:
        s = df[col].astype(str).str.replace(',', '')
        df[col] = s.astype(float)
        
    df['day'] = df['day'].astype('string')
    df['date'] = pd.to_datetime(df['date'])

    return df

def sales_by_category(report: str):
    print("Processing: Sales by Category")
    
    price_re = re.compile(r"\.\d{2}\s*$")
    df_attributes = ['description', 'quantity', 'gross_sale']
    rows = []
    
    for line in report.splitlines():
        line = line.rstrip("\n")
        if price_re.search(line):
            data = line.split()
            rows.append(data)
    
    df = pd.DataFrame(rows,columns=df_attributes)
            
    df['description'] = df['description'].astype('string')
    df['quantity'] = df['quantity'].astype(int)
    df['gross_sale'] = df['gross_sale'].astype(str).str.replace('$', '').astype(float)
    
    return df

def sales_by_customer(report: str):
    print("Processing: Sales by Customer")
    price_re = re.compile(r"\.\d{2}\s*$")

    curr_name = None
    curr_date = None
    df_attributes = ['customer', 'date', 'qty', 'sales_gst_inc', 'sales_gst_exc']
    rows = []


    
    for line in report.splitlines():
        line = line.rstrip("\n")
        if not line.strip() or line.startswith('Total'):
            continue
        
        if price_re.search(line):
            data = line.split()
        
            if len(data) > 4:
                
                curr_name = " ".join(data[:-4])
                name = curr_name.split(', ')
                name.reverse()
                curr_name = " ".join(name).strip().title()
                
                curr_date = data[-4]
                
                data = [curr_name] + [curr_date] + data[-3:]
                
            elif len(data) == 4:
                curr_date = data[0]
                data = [curr_name] + [curr_date] + data[-3:]
        
            elif  len(data) == 3:
                data = [curr_name] + [curr_date] + data
        
            else:
                pass
            
            # print(data)
            rows.append(data)
                    
                
    df = pd.DataFrame(rows,columns=df_attributes)

    df['customer'] = df['customer'].astype('string')
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    df['qty'] = df['qty'].astype(int)

    df['sales_gst_inc'] = (
        df['sales_gst_inc']
        .astype(str)
        .str.replace(',','',regex=False)
        .astype(float)
    )

    df['sales_gst_exc'] = (
        df['sales_gst_exc']
        .astype(str)
        .str.replace(',','',regex=False)
        .astype(float)
    )

    df = df.sort_values(by=['customer', 'date'], ascending=[True, True]).reset_index(drop=True)

    return df

def sales_by_sub_dept(report: str):
    print("Processing: Sales by Sub Department")

    # define column specifications: (start, end) positions
    colspecs = [
        (0, 2),    # dept
        (3, 4),    # sub_dept
        (4, 29),   # combined type-description
        (29, 36),  # quantity
        (36, None) # gross_sale
    ]
    report_io = io.StringIO(report)

    # read the fixed-width file, skipping header and footer
    df = pd.read_fwf(
        report_io,
        skiprows=6,
        skipfooter=12,
        colspecs=colspecs,
        names=['dept','sub_dept','category','quantity','gross_sale'],
        engine='python'
    )

    # split 'category' into 'type' and 'description'
    df[['type','description']] = (
        df['category']
        .str.split(r'-\s*', n=1, expand=True)
    )

    # clean up whitespace
    for c in ['dept','sub_dept','type','description']:
        df[c] = df[c].str.strip()

    # convert numeric columns
    df['quantity']   = df['quantity'].astype(int)
    df['gross_sale'] = (
        df['gross_sale']
        .str.replace(r'[\$,]', '', regex=True)
        .astype(float)
    )

    df = df[['dept','sub_dept','type','description','quantity','gross_sale']]

    return df

def stock_refill(report: str):
    print("Processing: Stock Refill")

    # 1. Define where each column lives (start, end) in the text file:
    colspecs = [
        (0, 11),   # product code
        (11,22),   # colour
        (22,39),   # name
        (39,47),   # size
        (47,53),   # sold
        (53,None)  # soh
    ]

    # Convert string to file-like object
    report_io = io.StringIO(report)

    # 2. Read with read_fwf
    df = pd.read_fwf(
        report_io,
        skiprows=7,      # drop title, date, header lines
        skipfooter=4,    # drop the underscore + footer notes
        colspecs=colspecs,
        names=['product','colour','name','size','sold','soh'],
        engine='python'
    )

    # 4. (Optional) strip any stray whitespace
    for c in ['product','colour','name']:
        df[c] = df[c].str.strip()

    return df

def tender_breakdown_detail(report: str):
    print("Processing: Tender Breakdown Detail")

    price_re = re.compile(r"\.\d{2}\s*$")

    df_attributes = ['day', 'date', 'tender', 'docket_no', 'sales_rep', 'time', 'value']
    rows = []

    for line in report.splitlines():
        line = line.rstrip("\n")
        if "day" in line and "Total" not in line and "Birthday" not in line:
            day, date = line.split()
            # print(day,date)            
        if "Value" in line:
            tender = line[:17].strip()
            # print(tender)
        if price_re.search(line):
            if "Total" not in line:
                # print(line)
                docket_no = line[:14].strip()
                sales_rep = line[17:32].strip()
                time = line[32:40].strip()
                value = line[41:].strip()
                # print(dt_stamp)
                rows.append([day,date,tender,docket_no,sales_rep,time,value])
                    
    df = pd.DataFrame(rows,columns=df_attributes)
    df['value'] = (
        df['value']
        .astype(str)
        .str.replace(',','',regex=False)
        .astype(float)
    )
    df['time'] = pd.to_datetime(df['time'], dayfirst=True)
    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    str_cols = ['day','tender','docket_no','sales_rep']
    for col in str_cols:
        df[col] = df[col].astype('string')
    df = df.sort_values(by=['date', 'time'], ascending=[True, True])
    return df

def tender_breakdown_summary(report: str):
    print("Processing: Tender Breakdown Summary")

    price_re = re.compile(r"\.\d{2}\s*$")

    df_attributes = ['day', 'date', 'tender', 'value']
    rows = []

    
    for line in report.splitlines():
        line = line.rstrip("\n")
        if "TOTAL BY TENDER" in line:
            break
        if "day" in line and "Total" not in line and "Birthday" not in line:
            day, date = line.split()
        if price_re.search(line) and "Total" not in line:
            tender = line[:-10].strip()
            value = line[-10:].strip()
            rows.append([day,date,tender,value])

    df = pd.DataFrame(rows,columns=df_attributes)
    df['value'] = (
        df['value']
        .astype(str)
        .str.replace(',','',regex=False)
        .astype(float)
    )
    df['date']  = pd.to_datetime(df['date'], dayfirst=True)
    str_cols = ['day', 'tender']
    for col in str_cols:
        df[col] = df[col].astype('string')

    return df

