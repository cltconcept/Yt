import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log('[API/auto-process-full] Forwarding to backend:', backendUrl);
    console.log('[API/auto-process-full] Body:', body);
    
    const response = await fetch(`${backendUrl}/api/auto-process-full`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    console.log('[API/auto-process-full] Backend response:', response.status, data);
    
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error('[API/auto-process-full] Error:', error);
    return NextResponse.json(
      { detail: error.message || 'Erreur proxy' },
      { status: 500 }
    );
  }
}


