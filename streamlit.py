import streamlit as st
from urllib.error import URLError
import pandas as pd
import altair as alt
from datetime import datetime

sheets_to_fetch = ['caleb%20recap', 'yous%20recap', 'serbian%20recap', 'cryp%20esports']
names_to_fetch = ['Caleb', 'Yous', 'Serbian', 'Cryp Esports']

def get_UN_data(indices, truncate_index):
    # Define column names
    column_names = ['Name', 'Date', 'Play', 'Odds', 'Units Risked', 'Result', 'Units Won/Lost']

    combined_df = pd.DataFrame()

    selected_sheets = [sheets_to_fetch[idx] for idx in indices]
    selected_names = [names_to_fetch[idx] for idx in indices]

    for sheet_name, name in zip(selected_sheets, selected_names):
        # Read the data while skipping rows that contain the misnamed cells 
        spreadsheet = pd.read_csv(f'https://docs.google.com/spreadsheets/d/12sCC92_qOCOTEGDsst_elS7gT4I1ko2CmPBqg9Y6NEU/gviz/tq?tqx=out:csv&sheet={sheet_name}', header=None, skiprows=1)

        # Add person's name to the beginning of the DataFrame
        spreadsheet.insert(0, 'Name', name)

        # Truncate each row after the specified column index
        spreadsheet = spreadsheet.iloc[:, :truncate_index + 1]  # +2 to keep the columns up to the desired index

        # Assign column names
        spreadsheet.columns = column_names

        # Remove 'u' character from 'Units Won/Lost' column
        spreadsheet['Units Won/Lost'] = spreadsheet['Units Won/Lost'].astype(str).str.replace('u', '')

        # Convert 'Units Won/Lost' column to numeric
        spreadsheet['Units Won/Lost'] = pd.to_numeric(spreadsheet['Units Won/Lost'], errors='coerce')

        # Append modified spreadsheet to the combined DataFrame 
        combined_df = pd.concat([combined_df, spreadsheet], ignore_index=True)

    return combined_df

def filter_dataframe_by_column_value(dataframe, column_name, values_to_keep):
    # Convert NaN values to empty string or any other suitable placeholder
    dataframe[column_name].fillna('', inplace=True)

    return dataframe[dataframe[column_name].astype(str).str.contains('|'.join(values_to_keep))]

def main():
    try:
        # Title and removing excess space
        st.set_page_config(layout="wide")
        st.title("Notify Betting Recaps")
        st.markdown("""
            <style>
                   .block-container {
                        padding-top: 1rem;
                        padding-bottom: 0rem;
                        padding-left: 5rem;
                        padding-right: 5rem;
                    }
            </style>
            """, unsafe_allow_html=True)

        # Allow 2 dropdowns side by side
        dropdown_columns = st.columns(2)
        table_columns = st.columns(2)

        # Select Betting Staff
        with dropdown_columns[0]:
            staff = st.multiselect(
                "Choose Staff Member(s)", names_to_fetch
            )

        if not staff:
            st.error("Please select at least one staff memeber and at least 2 dates or All.")
        else:
            # Get the indices of selected items
            indices = [names_to_fetch.index(name) for name in staff]

            df = get_UN_data(indices, 6)

            # Select date(s) you want
            # Gets the current date
            date_options = ["All"]
            current_month = datetime.now().month
            current_year = datetime.now().year
            monthyear = ""
            if current_month > 9:
                monthyear = str(current_month) + "/" + str(current_year)
                current_year = int(str(current_year))
            else:
                monthyear = "0" + str(current_month) + "/" + str(current_year)
                current_month = int("0" + str(current_month))
                current_year = int(str(current_year))
            # Gets a list of available dates
            start_month = 3
            start_year = 2023
            while True:
                date_options.append(str(start_month) + "/" + str(start_year))
                if start_month >= current_month and start_year >= current_year:
                    break
                if start_month == 12:
                    start_year = start_year + 1
                    start_month = 1
                else:
                    start_month = start_month + 1

            with dropdown_columns[1]:
                dates = st.multiselect(
                    'What date(s) to filter? (XX/MM/YY)',
                    date_options
                )

            # Convert the 'Date' to datetime format
            df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y')

            # Reformat the date to 'dd/mm/yyyy' format as a string
            df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')

            # Filter the DataFrame based on selected dates
            if not dates or (len(dates) < 2 and "All" not in dates):
                st.error("Please select at least 2 dates or All.")
            else:
                if "All" in dates:
                    filtered_df = df
                else:
                    filtered_df = filter_dataframe_by_column_value(df, 'Date', dates)
                
                with table_columns[0]:
                    st.write("List of Selected Staff and Dates.", filtered_df)

                # Convert the 'Date' column to datetime with month and year only
                filtered_df['Date'] = pd.to_datetime(filtered_df['Date'], format='%d/%m/%Y').dt.to_period('M')

                name_count = filtered_df.groupby('Name')['Units Won/Lost'].count().reset_index()
                name_count.columns = ['Name', 'Total Bets']

                # Group by 'Date' and 'Name', summing 'Profit_Loss'
                grouped = filtered_df.groupby(['Date', 'Name'])['Units Won/Lost'].sum().unstack(fill_value=0)
                
                # Reset index to access 'Date' and 'Name' as columns for plotting
                grouped = grouped.reset_index()

                # Streamlit app
                st.title('Month-to-month PnL (Units)')

                # Melt the DataFrame to long format for Altair
                melted = pd.melt(grouped, id_vars='Date', var_name='Name', value_name='Units W/L (Monthly)')

                # Calculate the sum of 'Units W/L' for each 'Name'
                name_total = melted.groupby('Name')['Units W/L (Monthly)'].sum().reset_index()
                name_total.columns = ["Name", "Units W/L"]

                name_summary = pd.merge(name_total, name_count, on='Name')

                with table_columns[1]:
                    st.write("Summary Over Selected Period", name_summary)

                # Convert 'Date' back to datetime format from period
                melted['Date'] = melted['Date'].dt.to_timestamp()

                # Create an Altair chart
                line = alt.Chart(melted).mark_line().encode(
                    x='Date:T',
                    y='Units W/L (Monthly):Q',
                    color='Name:N'
                ).properties(
                    width=800,
                    height=400
                )

                # Create an Altair chart
                circles = alt.Chart(melted).mark_circle().encode(
                    x='Date:T',
                    y='Units W/L (Monthly):Q',
                    color='Name:N'
                ).properties(
                    width=800,
                    height=400
                )

                chart = line + circles

                # Show the Altair chart in Streamlit
                st.altair_chart(chart, use_container_width=True)

    except URLError as e:
        st.error(
            """
            **This demo requires internet access.**
            Connection error: %s
        """
            % e.reason
        )

    except Exception as e:
        st.error("Failed to fetch data. Please check the Google Sheet URL.")
        st.error(e)

if __name__ == "__main__":
    main()