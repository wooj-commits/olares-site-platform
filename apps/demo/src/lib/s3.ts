import {
  S3Client,
  PutObjectCommand,
  ListObjectsV2Command,
  GetObjectCommand,
  DeleteObjectCommand,
  CreateBucketCommand,
  HeadBucketCommand,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

export function minioConfigured() {
  return Boolean(
    process.env.MINIO_ENDPOINT &&
      process.env.MINIO_ACCESS_KEY &&
      process.env.MINIO_SECRET_KEY &&
      process.env.MINIO_BUCKET,
  );
}

export function getBucket() {
  return process.env.MINIO_BUCKET || "olaresdemo";
}

export function getS3() {
  const endpoint = process.env.MINIO_ENDPOINT || "";
  const useSsl = String(process.env.MINIO_USE_SSL || "false").toLowerCase() === "true";
  const protocol = useSsl ? "https" : "http";
  const url = endpoint.startsWith("http") ? endpoint : `${protocol}://${endpoint}`;
  return new S3Client({
    region: "us-east-1",
    endpoint: url,
    forcePathStyle: true,
    credentials: {
      accessKeyId: process.env.MINIO_ACCESS_KEY || "",
      secretAccessKey: process.env.MINIO_SECRET_KEY || "",
    },
  });
}

export async function ensureBucket() {
  if (!minioConfigured()) return;
  const s3 = getS3();
  const Bucket = getBucket();
  try {
    await s3.send(new HeadBucketCommand({ Bucket }));
  } catch {
    try {
      await s3.send(new CreateBucketCommand({ Bucket }));
    } catch {
      // race / already exists
    }
  }
}

export { PutObjectCommand, ListObjectsV2Command, GetObjectCommand, DeleteObjectCommand, getSignedUrl };
