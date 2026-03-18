import mongoose from 'mongoose';
import type { ConnectOptions } from 'mongoose';

type CachedType = {
  conn: typeof mongoose | null;
  promise: Promise<typeof mongoose> | null;
};

declare global {
  var mongoose: CachedType | undefined;
}

const MONGODB_URI = process.env.MONGODB_URI!; 

if (!MONGODB_URI) {
  throw new Error('Please define the MONGODB_URI environment variable inside .env.local');
}

let cached = global.mongoose;

if (!cached) {
  cached = global.mongoose = { conn: null, promise: null };
}

async function dbConnect() {
  if (cached && cached.conn) return cached.conn;

  if (cached && !cached.promise) {
    const opts = {
      bufferCommands: false,
    } as ConnectOptions;

    cached.promise = mongoose.connect(MONGODB_URI, opts).then((mongooseInstance) => {
      return mongooseInstance;
    });
  }
  
  if (cached && cached.promise) {
    cached.conn = await cached.promise;
    return cached.conn;
  }
  
  throw new Error('Failed to connect to database');
}

export default dbConnect;