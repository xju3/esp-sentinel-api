from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ..services.mqtt_service import mqtt_service
from ..core.logging import setup_logging

logger = setup_logging()
router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Sentinel Server API"}

@router.get("/health")
async def health():
    return {"status": "healthy"}

@router.get("/machines")
async def get_machines():
    return {"machines": mqtt_service.get_all_machines()}

@router.get("/machine/{sn}")
async def get_machine_status(sn: int):
    data = mqtt_service.get_machine_data(sn)
    if data:
        return data.dict()
    raise HTTPException(status_code=404, detail="Machine not found")

@router.get("/machine-events")
async def query_machine_events(
    sn: int | None = None,
    day: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
):
    try:
        events = mqtt_service.query_machine_events(sn=sn, day=day, start_at=start_at, end_at=end_at, limit=limit)
        return {"events": events}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying machine events: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/machine-events-view", response_class=HTMLResponse)
async def machine_events_view():
    return """
            <!DOCTYPE html>
            <html lang='en'>
            <head>
                <meta charset='UTF-8' />
                <meta name='viewport' content='width=device-width, initial-scale=1.0' />
                <title>Machine Event Viewer</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; }
                    th { background: #f2f2f2; }
                    input, button { padding: 6px; margin-right: 6px; }
                </style>
            </head>
            <body>
                <h1>Machine Event Viewer</h1>
                <div>
                    <label>SN: <input id='sn' type='number' min='0' /></label>
                    <label>Day: <input id='day' type='date' /></label>
                    <label>Start: <input id='start_at' type='datetime-local' /></label>
                    <label>End: <input id='end_at' type='datetime-local' /></label>
                    <label>Limit: <input id='limit' type='number' min='1' value='20' /></label>
                    <button onclick='load()'>Load</button>
                </div>
                <table id='data-table'>
                    <thead id='table-head'></thead>
                    <tbody id='table-body'></tbody>
                </table>

                <script>
                    async function load() {
                        const sn = document.getElementById('sn').value;
                        const day = document.getElementById('day').value;
                        const start_at = document.getElementById('start_at').value;
                        const end_at = document.getElementById('end_at').value;
                        const limit = document.getElementById('limit').value || 20;
                        const params = new URLSearchParams();
                        if (sn) params.set('sn', sn);
                        if (day) params.set('day', day);
                        if (start_at) params.set('start_at', new Date(start_at).toISOString());
                        if (end_at) params.set('end_at', new Date(end_at).toISOString());
                        if (limit) params.set('limit', limit);

                        const res = await fetch('/machine-events?' + params);
                        const data = await res.json();
                        const tableHead = document.getElementById('table-head');
                        const tableBody = document.getElementById('table-body');

                        tableHead.innerHTML = '';
                        tableBody.innerHTML = '';

                        if (!data.events || data.events.length === 0) {
                            tableBody.insertAdjacentHTML('beforeend', '<tr><td colspan="100%">No events available</td></tr>');
                            return;
                        }

                        const columns = Object.keys(data.events[0]);
                        const groupNames = ['rms', 'peak', 'crest', 'impulse'];
                        const groupMap = {
                            rms: [],
                            peak: [],
                            crest: [],
                            impulse: []
                        };
                        const standardCols = [];

                        columns.forEach(col => {
                            const m = col.match(/^(rms|peak|crest|impulse)_([^_]+)$/i);
                            if (m) {
                                const g = m[1].toLowerCase();
                                groupMap[g].push({col, sub: m[2]});
                            } else {
                                standardCols.push(col);
                            }
                        });

                        const firstRowCells = [];
                        const secondRowCells = [];

                        standardCols.forEach(col => {
                            firstRowCells.push(`<th rowspan='2'>${col}</th>`);
                        });

                        groupNames.forEach(group => {
                            if (groupMap[group].length > 0) {
                                firstRowCells.push(`<th colspan='${groupMap[group].length}'>${group.toUpperCase()}</th>`);
                                groupMap[group].sort((a,b)=>a.sub.localeCompare(b.sub));
                                groupMap[group].forEach(item => {
                                    secondRowCells.push(`<th>${item.sub.toUpperCase()}</th>`);
                                });
                            }
                        });

                        let headerHtml = `<tr>${firstRowCells.join('')}</tr>`;
                        if (secondRowCells.length > 0) {
                            headerHtml += `<tr>${secondRowCells.join('')}</tr>`;
                        }
                        tableHead.innerHTML = headerHtml;

                        for (const event of data.events) {
                            const cellValues = [];
                            standardCols.forEach(col => {
                                cellValues.push(`<td>${event[col] ?? ''}</td>`);
                            });

                            groupNames.forEach(group => {
                                if (groupMap[group].length > 0) {
                                    groupMap[group].forEach(item => {
                                        cellValues.push(`<td>${event[item.col] ?? ''}</td>`);
                                    });
                                }
                            });

                            tableBody.insertAdjacentHTML('beforeend', `<tr>${cellValues.join('')}</tr>`);
                        }
                    }
                    window.onload = load;
                </script>
            </body>
            </html>
        """