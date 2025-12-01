import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log('[API/merge] Forwarding to backend:', backendUrl);
    
    const response = await fetch(`${backendUrl}/api/merge`, {
      method: 'POST',
      body: formData,
    });

    const data = await response.json();
    
    console.log('[API/merge] Backend response:', response.status, data);
    
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error('[API/merge] Error:', error);
    return NextResponse.json(
      { detail: error.message || 'Erreur proxy' },
      { status: 500 }
    );
  }
}

