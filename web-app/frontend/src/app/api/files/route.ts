import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    
    console.log('[API/files] Fetching from backend:', `${backendUrl}/api/files`);
    
    // Forcer le non-cache
    const response = await fetch(`${backendUrl}/api/files`, {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
      },
    });
    
    const data = await response.json();
    
    console.log('[API/files] Backend returned:', data.files?.length || 0, 'files');
    
    return NextResponse.json(data, { 
      status: response.status,
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
      },
    });
  } catch (error: any) {
    console.error('[API/files] Error:', error);
    return NextResponse.json(
      { files: [], error: error.message },
      { status: 500 }
    );
  }
}

