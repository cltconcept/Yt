import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { folder_name: string } }
) {
  try {
    const folder_name = params.folder_name;
    
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log('[API/auto-process-full/progress] Getting progress for:', folder_name);
    
    const response = await fetch(`${backendUrl}/api/auto-process-full/progress/${folder_name}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    console.log('[API/auto-process-full/progress] Backend response:', response.status);
    
    return NextResponse.json(data, { status: response.status });
  } catch (error: any) {
    console.error('[API/auto-process-full/progress] Error:', error);
    return NextResponse.json(
      { detail: error.message || 'Erreur proxy' },
      { status: 500 }
    );
  }
}


